import pytest
from httpx import AsyncClient
from tests.fixtures import mock_normal_user, mock_admin_user
from app.models.rule_approval import ApprovalStatus
from app.models.user import User, UserRole
import uuid

@pytest.fixture(autouse=True)
async def setup_mock_users():
    from app.core.database import async_session_maker
    from sqlalchemy import select
    
    async with async_session_maker() as session:
        # Check and handle Normal User
        res_normal = await session.execute(select(User).where(User.email == mock_normal_user.email))
        existing_normal = res_normal.scalar_one_or_none()
        if existing_normal:
            mock_normal_user.id = existing_normal.id
            existing_normal.role = UserRole.USER
            existing_normal.is_admin = False
        else:
            session.add(mock_normal_user)
            
        # Check and handle Admin User
        res_admin = await session.execute(select(User).where(User.email == mock_admin_user.email))
        existing_admin = res_admin.scalar_one_or_none()
        if existing_admin:
            mock_admin_user.id = existing_admin.id
            existing_admin.role = UserRole.ADMIN
            existing_admin.is_admin = True
        else:
            session.add(mock_admin_user)
            
        await session.commit()
        
    yield



@pytest.mark.asyncio
async def test_init_and_list_policies(client: AsyncClient, override_user):
    """Test initializing and listing approval policies."""
    # Authenticate as admin to init policies
    override_user(mock_admin_user)
    
    # 1. Initialize policies
    init_res = await client.post("/api/v1/rule-engine/approvals/policies/init")
    assert init_res.status_code == 200
    assert "policies" in init_res.json()["message"]

    # 2. List policies
    list_res = await client.get("/api/v1/rule-engine/approvals/policies")
    assert list_res.status_code == 200
    policies = list_res.json()
    assert len(policies) > 0
    assert any(p["name"] == "全局拦截规则修改审批" for p in policies)


@pytest.mark.asyncio
async def test_create_and_process_change_request(client: AsyncClient, override_user):
    """Test full workflow of creating, reviewing, and deploying a change request."""
    # Ensure policies are initialized
    override_user(mock_admin_user)
    await client.post("/api/v1/rule-engine/approvals/policies/init")

    # 1. Create a change request requiring approval (global and fail severity)
    override_user(mock_normal_user)
    payload = {
        "change_type": "create",
        "proposed_rule_data": {
            "rule_name": "Test Global Fail Rule",
            "rule_type": "keyword",
            "rule_content": "test_pattern",
            "severity": "fail",
            "is_active": True,
            "logic_config": {}
        },
        "reason": "Security compliance requirements",
        "priority": "high"
    }
    
    create_res = await client.post("/api/v1/rule-engine/approvals/change-requests", json=payload)
    assert create_res.status_code == 200
    request_data = create_res.json()
    assert request_data["status"] == "pending"
    request_id = request_data["id"]

    # 2. Normal user tries to review (should fail with 403)
    override_user(mock_normal_user)
    review_payload = {
        "action": "approve",
        "comment": "LGTM"
    }
    review_res = await client.post(f"/api/v1/rule-engine/approvals/change-requests/{request_id}/review", json=review_payload)
    assert review_res.status_code == 403

    # 3. Admin reviews and approves
    override_user(mock_admin_user)
    review_res = await client.post(f"/api/v1/rule-engine/approvals/change-requests/{request_id}/review", json=review_payload)
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "approved"

    # 4. Admin deploys
    deploy_res = await client.post(f"/api/v1/rule-engine/approvals/change-requests/{request_id}/deploy")
    assert deploy_res.status_code == 200
    deployed_data = deploy_res.json()
    assert deployed_data["status"] == "deployed"
    assert deployed_data["rule_id"] is not None


@pytest.mark.asyncio
async def test_auto_approved_change_request(client: AsyncClient, override_user):
    """Test change request that automatically gets approved and deployed (doesn't trigger policy)."""
    # Ensure policies are initialized
    override_user(mock_admin_user)
    await client.post("/api/v1/rule-engine/approvals/policies/init")

    override_user(mock_normal_user)
    
    # A global rule with severity = "warning" and rule_type = "keyword" won't match any approval policies.
    # Therefore, it should be auto-approved and deployed immediately.
    payload = {
        "change_type": "create",
        "proposed_rule_data": {
            "rule_name": "Test Auto Approved Warning Rule",
            "rule_type": "keyword",
            "rule_content": "auto_pattern",
            "severity": "warning",
            "is_active": True,
            "logic_config": {}
        },
        "reason": "Low risk warning rule addition",
        "priority": "low",
        "category_id": None
    }
    
    create_res = await client.post("/api/v1/rule-engine/approvals/change-requests", json=payload)
    assert create_res.status_code == 200
    res_data = create_res.json()
    assert res_data["status"] == "deployed"
    assert res_data["rule_id"] is not None

