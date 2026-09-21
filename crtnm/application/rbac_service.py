"""RBAC management service."""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from crtnm.application.audit_service import AuditService
from crtnm.domain.enums import UserRole
from crtnm.infrastructure.models import (
    Permission, Role, RolePermission, 
    User, UserRoleLink
)


class RBACService:
    """Manages roles, permissions, and user-role assignments."""
    
    # Default permissions for each role type
    DEFAULT_PERMISSIONS = {
        UserRole.SUPER_ADMIN: ["*"],  # All permissions
        UserRole.NETWORK_ADMIN: [
            "device.read", "device.create", "device.update", "device.delete",
            "config.read", "config.backup", "config.deploy",
            "alarm.ack", "alarm.resolve",
            "user.read",
        ],
        UserRole.NETWORK_ENGINEER: [
            "device.read", "device.create", "device.update",
            "config.read", "config.backup",
            "alarm.ack",
        ],
        UserRole.OPERATOR: [
            "device.read",
            "config.read", "config.backup",
            "alarm.ack",
        ],
        UserRole.VIEWER: [
            "device.read",
            "config.read",
            "alarm.read",
        ],
        UserRole.AUDITOR: [
            "device.read",
            "config.read",
            "alarm.read",
            "audit.read",
        ],
    }
    
    def __init__(self, audit: AuditService) -> None:
        self._audit = audit
    
    def initialize_default_roles(self, session: Session) -> None:
        """Create default system roles if they don't exist."""
        for role_name in UserRole:
            existing = session.scalar(
                select(Role).where(Role.name == role_name.value)
            )
            if not existing:
                role = Role(
                    name=role_name.value,
                    description=f"Default {role_name.value.replace('_', ' ')} role",
                    is_system=True,
                )
                session.add(role)
                session.flush()
                
                # Assign default permissions
                permissions = self.DEFAULT_PERMISSIONS.get(role_name, [])
                if permissions and permissions != ["*"]:
                    for perm in permissions:
                        resource, action = perm.split(".", 1) if "." in perm else (perm, "*")
                        permission = session.scalar(
                            select(Permission).where(
                                Permission.resource == resource,
                                Permission.action == action,
                            )
                        )
                        if not permission:
                            permission = Permission(
                                name=perm,
                                resource=resource,
                                action=action,
                                description=f"Permission to {action} {resource}",
                            )
                            session.add(permission)
                            session.flush()
                        
                        session.add(RolePermission(
                            role_id=role.id,
                            permission_id=permission.id,
                        ))
        
        session.commit()
    
    def create_permission(
        self, 
        session: Session, 
        actor: str,
        name: str, 
        resource: str, 
        action: str,
        description: str | None = None,
    ) -> Permission:
        """Create a new permission."""
        existing = session.scalar(
            select(Permission).where(Permission.name == name)
        )
        if existing:
            raise ValueError(f"Permission '{name}' already exists")
        
        permission = Permission(
            name=name,
            resource=resource,
            action=action,
            description=description,
        )
        session.add(permission)
        self._audit.record(
            session, actor, "permission.create", name,
            f"Resource: {resource}, Action: {action}"
        )
        session.commit()
        session.refresh(permission)
        return permission
    
    def create_role(
        self,
        session: Session,
        actor: str,
        name: str,
        description: str | None = None,
        permission_ids: list[int] | None = None,
    ) -> Role:
        """Create a new role with optional permissions."""
        existing = session.scalar(
            select(Role).where(Role.name == name)
        )
        if existing:
            raise ValueError(f"Role '{name}' already exists")
        
        role = Role(
            name=name,
            description=description,
            is_system=False,
        )
        session.add(role)
        session.flush()
        
        if permission_ids:
            for perm_id in permission_ids:
                session.add(RolePermission(
                    role_id=role.id,
                    permission_id=perm_id,
                ))
        
        self._audit.record(
            session, actor, "role.create", name,
            f"Permissions: {len(permission_ids or [])}"
        )
        session.commit()
        session.refresh(role)
        return role
    
    def assign_role_to_user(
        self,
        session: Session,
        actor: str,
        user_id: int,
        role_id: int,
    ) -> None:
        """Assign a role to a user."""
        user = session.get(User, user_id)
        if not user:
            raise LookupError(f"User {user_id} not found")
        
        role = session.get(Role, role_id)
        if not role:
            raise LookupError(f"Role {role_id} not found")
        
        # Check if already assigned
        existing = session.scalar(
            select(UserRoleLink).where(
                UserRoleLink.user_id == user_id,
                UserRoleLink.role_id == role_id,
            )
        )
        if existing:
            raise ValueError(f"User {user_id} already has role {role.name}")
        
        session.add(UserRoleLink(user_id=user_id, role_id=role_id))
        self._audit.record(
            session, actor, "user.role.assign", 
            f"user:{user_id}", f"Role: {role.name}"
        )
        session.commit()
    
    def remove_role_from_user(
        self,
        session: Session,
        actor: str,
        user_id: int,
        role_id: int,
    ) -> None:
        """Remove a role from a user."""
        assignment = session.scalar(
            select(UserRoleLink).where(
                UserRoleLink.user_id == user_id,
                UserRoleLink.role_id == role_id,
            )
        )
        if not assignment:
            raise LookupError(f"User {user_id} does not have role {role_id}")
        
        session.delete(assignment)
        self._audit.record(
            session, actor, "user.role.remove",
            f"user:{user_id}", f"Role ID: {role_id}"
        )
        session.commit()
    
    def get_user_permissions(self, session: Session, user_id: int) -> set[str]:
        """Get all permissions for a user based on their roles."""
        user = session.get(User, user_id)
        if not user:
            return set()
        
        # Superusers have all permissions
        if user.is_superuser:
            return {"*"}
        
        permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                permissions.add(perm.name)
        
        return permissions
    
    def has_permission(self, session: Session, user_id: int, permission: str) -> bool:
        """Check if a user has a specific permission."""
        user_permissions = self.get_user_permissions(session, user_id)
        return "*" in user_permissions or permission in user_permissions
    
    def list_roles(self, session: Session) -> list[Role]:
        """List all roles with their permissions."""
        return list(session.scalars(
            select(Role).options(joinedload(Role.permissions))
        ))
    
    def list_permissions(self, session: Session) -> list[Permission]:
        """List all permissions."""
        return list(session.scalars(select(Permission).order_by(Permission.name)))
