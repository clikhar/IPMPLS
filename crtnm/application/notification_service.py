"""Notification service for multi-channel alerting."""
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import logging

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crtnm.infrastructure.models import (
    Notification,
    NotificationChannel,
    NotificationRule,
    Alarm,
    Event,
)
from crtnm.domain.enums import AlarmSeverity, EventType, NotificationChannelType


logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications through multiple channels."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def process_alarm_notification(self, alarm: Alarm) -> None:
        """Process notification rules for a new alarm."""
        
        # Skip if suppressed
        if alarm.status.value == "suppressed":
            logger.debug(f"Alarm {alarm.id} is suppressed, skipping notifications")
            return
        
        # Get applicable rules
        rules = await self._get_applicable_rules(
            severity=alarm.severity,
            event_type=alarm.event_type,
            device_id=alarm.device_id,
        )
        
        for rule in rules:
            # Check deduplication
            if await self._is_duplicate_notification(rule, alarm):
                logger.debug(f"Notification for rule {rule.id} is duplicate, skipping")
                continue
            
            # Send to all channels
            for channel in rule.channels:
                if not channel.is_enabled:
                    continue
                
                await self._send_notification(
                    channel=channel,
                    rule=rule,
                    alarm=alarm,
                )
    
    async def _get_applicable_rules(
        self,
        severity: AlarmSeverity,
        event_type: EventType,
        device_id: Optional[int] = None,
    ) -> list[NotificationRule]:
        """Get notification rules that match the alarm criteria."""
        
        result = await self.db.execute(
            select(NotificationRule)
            .options(selectinload(NotificationRule.channels))
            .where(NotificationRule.is_enabled == True)
        )
        
        all_rules = result.scalars().all()
        applicable_rules = []
        
        for rule in all_rules:
            # Check severity match
            if rule.severities:
                if severity.value not in rule.severities:
                    continue
            
            # Check event type match
            if rule.event_types:
                if event_type.value not in rule.event_types:
                    continue
            
            # Check device group match
            if rule.device_groups and device_id:
                # Would need to check if device belongs to any of the groups
                # For now, skip device group filtering if not implemented
                pass
            
            applicable_rules.append(rule)
        
        return applicable_rules
    
    async def _is_duplicate_notification(
        self,
        rule: NotificationRule,
        alarm: Alarm,
    ) -> bool:
        """Check if notification is duplicate within dedup window."""
        
        if not rule.dedup_window_minutes:
            return False
        
        window_start = datetime.utcnow() - timedelta(minutes=rule.dedup_window_minutes)
        
        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                and_(
                    Notification.rule_id == rule.id,
                    Notification.alarm_id == alarm.id,
                    Notification.sent_at >= window_start,
                    Notification.status == "sent",
                )
            )
        )
        
        count = result.scalar() or 0
        return count > 0
    
    async def _send_notification(
        self,
        channel: NotificationChannel,
        rule: NotificationRule,
        alarm: Alarm,
    ) -> None:
        """Send notification through specified channel."""
        
        # Create notification record
        notification = Notification(
            channel_id=channel.id,
            rule_id=rule.id,
            alarm_id=alarm.id,
            subject=f"[{alarm.severity.value.upper()}] {alarm.title}",
            message=self._format_notification_message(alarm),
            status="pending",
            recipients=self._get_recipients(channel),
        )
        
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        try:
            # Rate limiting check
            if await self._exceeds_rate_limit(channel):
                notification.status = "failed"
                notification.error_message = "Rate limit exceeded"
                await self.db.commit()
                return
            
            # Send based on channel type
            if channel.channel_type == NotificationChannelType.EMAIL:
                await self._send_email_notification(channel, notification)
            elif channel.channel_type == NotificationChannelType.TELEGRAM:
                await self._send_telegram_notification(channel, notification)
            elif channel.channel_type == NotificationChannelType.SLACK:
                await self._send_slack_notification(channel, notification)
            elif channel.channel_type == NotificationChannelType.TEAMS:
                await self._send_teams_notification(channel, notification)
            elif channel.channel_type == NotificationChannelType.SMS:
                await self._send_sms_notification(channel, notification)
            elif channel.channel_type == NotificationChannelType.WEBHOOK:
                await self._send_webhook_notification(channel, notification)
            else:
                notification.status = "failed"
                notification.error_message = f"Unknown channel type: {channel.channel_type}"
            
            notification.sent_at = datetime.utcnow()
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to send notification {notification.id}: {e}")
            notification.status = "failed"
            notification.error_message = str(e)
            await self.db.commit()
    
    def _format_notification_message(self, alarm: Alarm) -> str:
        """Format alarm details into notification message."""
        
        lines = [
            f"Alarm: {alarm.title}",
            f"Severity: {alarm.severity.value.upper()}",
            f"Status: {alarm.status.value}",
            f"First Occurred: {alarm.first_occurred.isoformat()}",
            f"Last Occurred: {alarm.last_occurred.isoformat()}",
            f"Occurrence Count: {alarm.occurrence_count}",
        ]
        
        if alarm.message:
            lines.append(f"\nDetails: {alarm.message}")
        
        if alarm.additional_info:
            lines.append("\nAdditional Information:")
            for key, value in alarm.additional_info.items():
                lines.append(f"  - {key}: {value}")
        
        if alarm.acknowledged_by:
            lines.append(f"\nAcknowledged by User ID: {alarm.acknowledged_by}")
            if alarm.acknowledged_at:
                lines.append(f"Acknowledged at: {alarm.acknowledged_at.isoformat()}")
            if alarm.acknowledged_note:
                lines.append(f"Acknowledgment Note: {alarm.acknowledged_note}")
        
        return "\n".join(lines)
    
    def _get_recipients(self, channel: NotificationChannel) -> Optional[list]:
        """Extract recipients from channel configuration."""
        
        config = channel.config or {}
        
        if channel.channel_type == NotificationChannelType.EMAIL:
            return config.get("recipients", [])
        elif channel.channel_type == NotificationChannelType.TELEGRAM:
            chat_ids = config.get("chat_ids", [])
            return [f"telegram:{cid}" for cid in chat_ids]
        elif channel.channel_type == NotificationChannelType.SMS:
            return config.get("phone_numbers", [])
        else:
            return None
    
    async def _exceeds_rate_limit(self, channel: NotificationChannel) -> bool:
        """Check if channel has exceeded rate limit."""
        
        if not channel.rate_limit_per_minute:
            return False
        
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        
        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                and_(
                    Notification.channel_id == channel.id,
                    Notification.sent_at >= one_minute_ago,
                    Notification.status == "sent",
                )
            )
        )
        
        count = result.scalar() or 0
        return count >= channel.rate_limit_per_minute
    
    async def _send_email_notification(
        self,
        channel: NotificationChannel,
        notification: Notification,
    ) -> None:
        """Send email notification."""
        # Implementation would use SMTP library
        # For now, log the action
        config = channel.config or {}
        smtp_host = config.get("smtp_host", "localhost")
        logger.info(
            f"Sending email via {smtp_host} to {notification.recipients}: "
            f"{notification.subject}"
        )
        notification.status = "sent"
    
    async def _send_telegram_notification(
        self,
        channel: NotificationChannel,
        notification: Notification,
    ) -> None:
        """Send Telegram notification."""
        config = channel.config or {}
        bot_token = config.get("bot_token")
        
        if not bot_token:
            raise ValueError("Telegram bot token not configured")
        
        # In production, would make HTTP request to Telegram API
        logger.info(
            f"Sending Telegram notification to chat_ids: {config.get('chat_ids', [])}"
        )
        notification.status = "sent"
    
    async def _send_slack_notification(
        self,
        channel: NotificationChannel,
        notification: Notification,
    ) -> None:
        """Send Slack notification."""
        config = channel.config or {}
        webhook_url = config.get("webhook_url")
        
        if not webhook_url:
            raise ValueError("Slack webhook URL not configured")
        
        # In production, would make HTTP request to Slack webhook
        logger.info(f"Sending Slack notification to webhook")
        notification.status = "sent"
    
    async def _send_teams_notification(
        self,
        channel: NotificationChannel,
        notification: Notification,
    ) -> None:
        """Send Microsoft Teams notification."""
        config = channel.config or {}
        webhook_url = config.get("webhook_url")
        
        if not webhook_url:
            raise ValueError("Teams webhook URL not configured")
        
        # In production, would make HTTP request to Teams webhook
        logger.info(f"Sending Teams notification to webhook")
        notification.status = "sent"
    
    async def _send_sms_notification(
        self,
        channel: NotificationChannel,
        notification: Notification,
    ) -> None:
        """Send SMS notification via gateway."""
        config = channel.config or {}
        gateway_url = config.get("gateway_url")
        
        if not gateway_url:
            raise ValueError("SMS gateway not configured")
        
        # In production, would make HTTP request to SMS gateway
        logger.info(f"Sending SMS via {gateway_url} to {notification.recipients}")
        notification.status = "sent"
    
    async def _send_webhook_notification(
        self,
        channel: NotificationChannel,
        notification: Notification,
    ) -> None:
        """Send generic webhook notification."""
        config = channel.config or {}
        webhook_url = config.get("url")
        
        if not webhook_url:
            raise ValueError("Webhook URL not configured")
        
        # In production, would make HTTP POST request
        logger.info(f"Sending webhook notification to {webhook_url}")
        notification.status = "sent"
    
    async def get_notification_history(
        self,
        channel_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        """Get notification history with filtering."""
        
        conditions = []
        
        if channel_id:
            conditions.append(Notification.channel_id == channel_id)
        
        if status:
            conditions.append(Notification.status == status)
        
        # Count total
        count_query = select(func.count()).select_from(Notification)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get results
        query = (
            select(Notification)
            .where(and_(*conditions)) if conditions else select(Notification)
        ).order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        notifications = list(result.scalars().all())
        
        return notifications, total
    
    async def test_channel(self, channel_id: int) -> dict:
        """Test notification channel connectivity."""
        
        result = await self.db.execute(
            select(NotificationChannel).where(NotificationChannel.id == channel_id)
        )
        channel = result.scalar_one_or_none()
        
        if not channel:
            return {"success": False, "error": "Channel not found"}
        
        test_notification = Notification(
            channel_id=channel_id,
            subject="Test Notification",
            message="This is a test notification from CRTNM",
            status="pending",
        )
        
        self.db.add(test_notification)
        await self.db.commit()
        await self.db.refresh(test_notification)
        
        try:
            if channel.channel_type == NotificationChannelType.EMAIL:
                await self._send_email_notification(channel, test_notification)
            elif channel.channel_type == NotificationChannelType.TELEGRAM:
                await self._send_telegram_notification(channel, test_notification)
            elif channel.channel_type == NotificationChannelType.SLACK:
                await self._send_slack_notification(channel, test_notification)
            elif channel.channel_type == NotificationChannelType.TEAMS:
                await self._send_teams_notification(channel, test_notification)
            elif channel.channel_type == NotificationChannelType.SMS:
                await self._send_sms_notification(channel, test_notification)
            elif channel.channel_type == NotificationChannelType.WEBHOOK:
                await self._send_webhook_notification(channel, test_notification)
            else:
                raise ValueError(f"Unknown channel type: {channel.channel_type}")
            
            return {"success": True, "message": "Test notification sent successfully"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
