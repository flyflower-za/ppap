"""
LDAP/SSO Configuration model
"""
from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime
from app.core.database import Base


class LDAPConfig(Base):
    """LDAP/SSO Configuration model for authentication setup."""

    __tablename__ = "ldap_config"

    id = Column(String(100), primary_key=True)  # Config key

    # LDAP Configuration
    ldap_enabled = Column(String(10), default="false")  # Enable LDAP authentication
    ldap_server = Column(String(500))  # LDAP server address
    ldap_port = Column(String(10))  # LDAP port (default: 389 or 636 for SSL)
    ldap_use_ssl = Column(String(10), default="false")  # Use SSL/TLS
    ldap_bind_dn = Column(String(500))  # Bind DN for authentication
    ldap_bind_password = Column(String(500))  # Bind password
    ldap_search_base = Column(String(500))  # Base DN for user search
    ldap_search_filter = Column(String(500))  # Search filter (e.g., "(sAMAccountName={username})")
    ldap_email_attribute = Column(String(100), default="mail")  # Email attribute
    ldap_name_attribute = Column(String(100), default="cn")  # Display name attribute
    ldap_department_attribute = Column(String(100), default="department")  # Department attribute

    # AD Group Mapping for Role Assignment
    ad_admin_group = Column(String(500))  # AD group DN for admin role
    ad_manager_group = Column(String(500))  # AD group DN for manager role
    ad_user_group = Column(String(500))  # AD group DN for user role (optional, all authenticated users)

    # SSO Configuration (SAML)
    sso_enabled = Column(String(10), default="false")  # Enable SSO authentication
    sso_provider = Column(String(100))  # SSO provider (e.g., "AzureAD", "Okta")
    sso_entity_id = Column(String(500))  # SAML Entity ID
    sso_acs_url = Column(String(500))  # Assertion Consumer Service URL
    sso_slo_url = Column(String(500))  # Single Logout URL
    sso_idp_sso_url = Column(String(500))  # Identity Provider SSO URL
    sso_idp_cert = Column(Text)  # Identity Provider X.509 Certificate
    sso_sp_cert = Column(Text)  # Service Provider X.509 Certificate
    sso_sp_key = Column(Text)  # Service Provider Private Key

    # General Settings
    local_admin_enabled = Column(String(10), default="true")  # Keep local admin account
    auto_create_users = Column(String(10), default="true")  # Auto-create users on first login
    default_role = Column(String(50), default="user")  # Default role for new users

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
