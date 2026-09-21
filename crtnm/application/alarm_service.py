"""Alarm management service with correlation and root cause analysis."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crtnm.infrastructure.models import (
    Alarm, Event, Device, Interface, User, NotificationRule, 
    NotificationChannel, Notification, MaintenanceWindow
)
from crtnm.domain.enums import AlarmSeverity, AlarmStatus, EventType


class AlarmService:
    """Service for alarm lifecycle management and correlation."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_alarm(
        self,
        event_type: EventType,
        severity: AlarmSeverity,
        title: str,
        message: str,
        device_id: Optional[int] = None,
        interface_id: Optional[int] = None,
        additional_info: Optional[dict] = None,
        correlated_events: Optional[list] = None,
    ) -> Alarm:
        """Create a new alarm with deduplication and correlation."""
        
        # Check if similar active alarm exists (deduplication)
        existing_alarm = await self._find_similar_alarm(
            event_type=event_type,
            device_id=device_id,
            interface_id=interface_id,
        )
        
        if existing_alarm:
            # Update existing alarm
            existing_alarm.last_occurred = datetime.utcnow()
            existing_alarm.occurrence_count += 1
            existing_alarm.severity = severity
            if additional_info:
                existing_additional = existing_alarm.additional_info or {}
                existing_additional.update(additional_info)
                existing_alarm.additional_info = existing_additional
            
            await self.db.commit()
            await self.db.refresh(existing_alarm)
            return existing_alarm
        
        # Check for maintenance window suppression
        suppressed, reason = await self._check_maintenance_window(
            device_id=device_id,
            severity=severity,
        )
        
        status = AlarmStatus.SUPPRESSED if suppressed else AlarmStatus.ACTIVE
        suppression_reason = reason if suppressed else None
        suppressed_until = None
        if suppressed and reason:
            # Extract until time from maintenance window if available
            pass
        
        # Create new alarm
        alarm = Alarm(
            title=title,
            message=message,
            event_type=event_type,
            severity=severity,
            status=status,
            device_id=device_id,
            interface_id=interface_id,
            additional_info=additional_info,
            correlated_events=correlated_events or [],
            suppression_reason=suppression_reason,
            suppressed_until=suppressed_until,
        )
        
        self.db.add(alarm)
        await self.db.commit()
        await self.db.refresh(alarm)
        
        # Perform root cause analysis
        await self._perform_root_cause_analysis(alarm)
        
        return alarm
    
    async def _find_similar_alarm(
        self,
        event_type: EventType,
        device_id: Optional[int] = None,
        interface_id: Optional[int] = None,
    ) -> Optional[Alarm]:
        """Find existing active alarm with same characteristics."""
        
        conditions = [
            Alarm.event_type == event_type,
            Alarm.status.in_([AlarmStatus.ACTIVE, AlarmStatus.ACKNOWLEDGED]),
        ]
        
        if device_id:
            conditions.append(Alarm.device_id == device_id)
        elif interface_id:
            conditions.append(Alarm.interface_id == interface_id)
        
        result = await self.db.execute(
            select(Alarm)
            .where(and_(*conditions))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _check_maintenance_window(
        self,
        device_id: Optional[int] = None,
        severity: Optional[AlarmSeverity] = None,
    ) -> tuple[bool, Optional[str]]:
        """Check if alarm should be suppressed due to maintenance window."""
        
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(MaintenanceWindow)
            .where(
                and_(
                    MaintenanceWindow.is_active == True,
                    MaintenanceWindow.start_time <= now,
                    MaintenanceWindow.end_time >= now,
                    MaintenanceWindow.suppress_notifications == True,
                )
            )
        )
        
        windows = result.scalars().all()
        
        for window in windows:
            # Check device scope
            if device_id and window.device_ids:
                if device_id not in window.device_ids:
                    continue
            
            # Check severity scope
            if severity and window.alarm_severities:
                if severity.value not in window.alarm_severities:
                    continue
            
            return True, f"Maintenance window: {window.name}"
        
        return False, None
    
    async def _perform_root_cause_analysis(self, alarm: Alarm) -> None:
        """Analyze alarm to identify potential root cause."""
        
        if not alarm.device_id:
            return
        
        # Get device hierarchy information
        result = await self.db.execute(
            select(Device)
            .options(
                selectinload(Device.site),
                selectinload(Device.parent_device),
            )
            .where(Device.id == alarm.device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return
        
        # Check if parent device has related alarms
        if device.parent_device_id:
            parent_alarms = await self._get_device_alarms(
                device_id=device.parent_device_id,
                statuses=[AlarmStatus.ACTIVE],
            )
            
            if parent_alarms:
                # Parent device alarm is likely root cause
                for parent_alarm in parent_alarms:
                    if self._is_related_alarm(parent_alarm, alarm):
                        alarm.root_cause_alarm_id = parent_alarm.id
                        alarm.is_root_cause = False
                        break
        
        # Check for upstream devices with alarms
        # This would require topology information
        
        await self.db.commit()
    
    def _is_related_alarm(self, parent_alarm: Alarm, child_alarm: Alarm) -> bool:
        """Determine if parent alarm is root cause of child alarm."""
        
        # Device down causes interface down
        if parent_alarm.event_type == EventType.DEVICE_DOWN:
            if child_alarm.event_type in [EventType.LINK_DOWN, EventType.DEVICE_DOWN]:
                return True
        
        # Power failure causes multiple downstream issues
        if parent_alarm.event_type == EventType.POWER_FAILURE:
            return True
        
        # High CPU/Memory can cause neighbor issues
        if parent_alarm.event_type in [EventType.CPU_HIGH, EventType.MEMORY_HIGH]:
            if child_alarm.event_type in [
                EventType.BGP_NEIGHBOR_DOWN,
                EventType.OSPF_NEIGHBOR_DOWN,
                EventType.ISIS_NEIGHBOR_DOWN,
                EventType.LDP_NEIGHBOR_DOWN,
            ]:
                return True
        
        return False
    
    async def acknowledge_alarm(
        self,
        alarm_id: int,
        user_id: int,
        note: Optional[str] = None,
    ) -> Optional[Alarm]:
        """Acknowledge an alarm."""
        
        result = await self.db.execute(
            select(Alarm).where(Alarm.id == alarm_id)
        )
        alarm = result.scalar_one_or_none()
        
        if not alarm:
            return None
        
        if alarm.status == AlarmStatus.RESOLVED:
            raise ValueError("Cannot acknowledge resolved alarm")
        
        alarm.acknowledged_by = user_id
        alarm.acknowledged_at = datetime.utcnow()
        alarm.acknowledged_note = note
        alarm.status = AlarmStatus.ACKNOWLEDGED
        
        await self.db.commit()
        await self.db.refresh(alarm)
        
        return alarm
    
    async def resolve_alarm(
        self,
        alarm_id: int,
        user_id: int,
        note: Optional[str] = None,
        resolve_children: bool = True,
    ) -> Optional[Alarm]:
        """Resolve an alarm and optionally its children."""
        
        result = await self.db.execute(
            select(Alarm).where(Alarm.id == alarm_id)
        )
        alarm = result.scalar_one_or_none()
        
        if not alarm:
            return None
        
        alarm.resolved_by = user_id
        alarm.resolved_at = datetime.utcnow()
        alarm.resolution_note = note
        alarm.status = AlarmStatus.RESOLVED
        
        # Resolve child alarms if this was root cause
        if resolve_children and alarm.is_root_cause:
            await self._resolve_child_alarms(alarm.id, user_id, note)
        
        # Check for corresponding clear events
        if alarm.event_type in self._CLEAR_EVENT_MAP:
            clear_event_type = self._CLEAR_EVENT_MAP[alarm.event_type]
            await self._create_clear_event(alarm, clear_event_type)
        
        await self.db.commit()
        await self.db.refresh(alarm)
        
        return alarm
    
    _CLEAR_EVENT_MAP = {
        EventType.LINK_DOWN: EventType.LINK_UP,
        EventType.DEVICE_DOWN: EventType.DEVICE_UP,
        EventType.BGP_NEIGHBOR_DOWN: EventType.BGP_NEIGHBOR_UP,
        EventType.OSPF_NEIGHBOR_DOWN: EventType.OSPF_NEIGHBOR_UP,
        EventType.ISIS_NEIGHBOR_DOWN: EventType.ISIS_NEIGHBOR_UP,
        EventType.LDP_NEIGHBOR_DOWN: EventType.LDP_NEIGHBOR_UP,
    }
    
    async def _resolve_child_alarms(
        self,
        root_alarm_id: int,
        user_id: int,
        note: str,
    ) -> None:
        """Resolve all child alarms of a root cause alarm."""
        
        result = await self.db.execute(
            select(Alarm)
            .where(
                and_(
                    Alarm.root_cause_alarm_id == root_alarm_id,
                    Alarm.status.in_([AlarmStatus.ACTIVE, AlarmStatus.ACKNOWLEDGED]),
                )
            )
        )
        
        child_alarms = result.scalars().all()
        
        for child_alarm in child_alarms:
            child_alarm.resolved_by = user_id
            child_alarm.resolved_at = datetime.utcnow()
            child_alarm.resolution_note = f"Auto-resolved: Root cause resolved - {note}"
            child_alarm.status = AlarmStatus.RESOLVED
    
    async def _create_clear_event(
        self,
        original_alarm: Alarm,
        clear_event_type: EventType,
    ) -> None:
        """Create a clearing event for the alarm."""
        
        clear_event = Event(
            source_type="system",
            source_ip=None,
            event_type=clear_event_type,
            device_id=original_alarm.device_id,
            interface_id=original_alarm.interface_id,
            severity=AlarmSeverity.INFO,
            message=f"Cleared: {original_alarm.title}",
            timestamp=datetime.utcnow(),
            processed=True,
            alarm_id=original_alarm.id,
        )
        
        self.db.add(clear_event)
    
    async def _get_device_alarms(
        self,
        device_id: int,
        statuses: Optional[list[AlarmStatus]] = None,
    ) -> list[Alarm]:
        """Get alarms for a specific device."""
        
        query = select(Alarm).where(Alarm.device_id == device_id)
        
        if statuses:
            query = query.where(Alarm.status.in_(statuses))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_active_alarms(
        self,
        device_id: Optional[int] = None,
        severity: Optional[AlarmSeverity] = None,
        status: Optional[AlarmStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Alarm], int]:
        """Get active alarms with filtering and pagination."""
        
        conditions = [
            Alarm.status.in_([AlarmStatus.ACTIVE, AlarmStatus.ACKNOWLEDGED])
        ]
        
        if device_id:
            conditions.append(Alarm.device_id == device_id)
        
        if severity:
            conditions.append(Alarm.severity == severity)
        
        if status:
            conditions.append(Alarm.status == status)
        
        # Count total
        count_query = select(func.count()).select_from(Alarm).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get results
        query = (
            select(Alarm)
            .where(and_(*conditions))
            .order_by(Alarm.last_occurred.desc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        alarms = list(result.scalars().all())
        
        return alarms, total
    
    async def get_alarm_statistics(self) -> dict:
        """Get alarm statistics for dashboard."""
        
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        # Current active alarms by severity
        active_query = select(
            Alarm.severity,
            func.count().label('count')
        ).where(
            Alarm.status.in_([AlarmStatus.ACTIVE, AlarmStatus.ACKNOWLEDGED])
        ).group_by(Alarm.severity)
        
        active_result = await self.db.execute(active_query)
        active_by_severity = {
            row.severity.value: row.count 
            for row in active_result.all()
        }
        
        # Alarms created in last 24 hours
        new_24h_query = select(func.count()).where(
            Alarm.first_occurred >= day_ago
        )
        new_24h_result = await self.db.execute(new_24h_query)
        new_24h = new_24h_result.scalar() or 0
        
        # Alarms resolved in last 24 hours
        resolved_24h_query = select(func.count()).where(
            Alarm.status == AlarmStatus.RESOLVED,
            Alarm.resolved_at >= day_ago
        )
        resolved_24h_result = await self.db.execute(resolved_24h_query)
        resolved_24h = resolved_24h_result.scalar() or 0
        
        # Mean time to acknowledge (MTTA)
        mtta_query = select(
            func.avg(Alarm.acknowledged_at - Alarm.first_occurred)
        ).where(
            Alarm.acknowledged_at.isnot(None),
            Alarm.first_occurred >= week_ago
        )
        mtta_result = await self.db.execute(mtta_query)
        mtta = mtta_result.scalar()
        
        # Mean time to resolve (MTTR)
        mttr_query = select(
            func.avg(Alarm.resolved_at - Alarm.first_occurred)
        ).where(
            Alarm.resolved_at.isnot(None),
            Alarm.resolved_at >= week_ago
        )
        mttr_result = await self.db.execute(mttr_query)
        mttr = mttr_result.scalar()
        
        return {
            "active_total": sum(active_by_severity.values()),
            "active_by_severity": active_by_severity,
            "new_24h": new_24h,
            "resolved_24h": resolved_24h,
            "mtta_seconds": mtta.total_seconds() if mtta else None,
            "mttr_seconds": mttr.total_seconds() if mttr else None,
        }
    
    async def suppress_alarm(
        self,
        alarm_id: int,
        until: datetime,
        reason: str,
    ) -> Optional[Alarm]:
        """Manually suppress an alarm."""
        
        result = await self.db.execute(
            select(Alarm).where(Alarm.id == alarm_id)
        )
        alarm = result.scalar_one_or_none()
        
        if not alarm:
            return None
        
        alarm.status = AlarmStatus.SUPPRESSED
        alarm.suppressed_until = until
        alarm.suppression_reason = reason
        
        await self.db.commit()
        await self.db.refresh(alarm)
        
        return alarm
    
    async def unsuppress_alarm(self, alarm_id: int) -> Optional[Alarm]:
        """Remove suppression from an alarm."""
        
        result = await self.db.execute(
            select(Alarm).where(Alarm.id == alarm_id)
        )
        alarm = result.scalar_one_or_none()
        
        if not alarm:
            return None
        
        alarm.status = AlarmStatus.ACTIVE
        alarm.suppressed_until = None
        alarm.suppression_reason = None
        
        await self.db.commit()
        await self.db.refresh(alarm)
        
        return alarm
