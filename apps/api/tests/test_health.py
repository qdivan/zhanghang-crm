from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_login_and_me():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "boss"


def test_billing_records():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        list_response = client.get("/api/v1/billing-records", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) >= 1

        customers_response = client.get("/api/v1/customers", headers=headers)
        assert customers_response.status_code == 200
        assert len(customers_response.json()) >= 1
        customer_id = customers_response.json()[0]["id"]

        create_response = client.post(
            "/api/v1/billing-records",
            headers=headers,
            json={
                "serial_no": 99,
                "customer_id": customer_id,
                "total_fee": 1000,
                "monthly_fee": 100,
                "billing_cycle_text": "2026/2/26收（2026.1-2026.12）",
                "due_month": "2026-12-31",
                "payment_method": "预收",
                "note": "测试记录",
            },
        )
        assert create_response.status_code == 201
        assert isinstance(create_response.json()["serial_no"], int)


def test_lead_detail_and_convert_customer_flow():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_lead = client.post(
            "/api/v1/leads",
            headers=headers,
            json={
                "template_type": "FOLLOWUP",
                "name": "转化测试公司",
                "contact_name": "李经理",
                "phone": "13800138000",
                "country": "跨境电商",
            },
        )
        assert create_lead.status_code == 201
        lead_id = create_lead.json()["id"]

        lead_detail = client.get(f"/api/v1/leads/{lead_id}", headers=headers)
        assert lead_detail.status_code == 200
        assert lead_detail.json()["name"] == "转化测试公司"

        accountants_resp = client.get("/api/v1/users", headers=headers, params={"role": "ACCOUNTANT"})
        assert accountants_resp.status_code == 200
        accountant = accountants_resp.json()[0]

        convert_resp = client.post(
            f"/api/v1/leads/{lead_id}/convert",
            headers=headers,
            json={
                "accountant_id": accountant["id"],
                "customer_name": "转化后客户名",
                "customer_contact_name": "转化后联系人",
                "customer_phone": "13911112222",
            },
        )
        assert convert_resp.status_code == 200
        customer_id = convert_resp.json()["customer"]["id"]

        customers_resp = client.get("/api/v1/customers", headers=headers)
        assert customers_resp.status_code == 200
        assert any(item["id"] == customer_id for item in customers_resp.json())

        customer_detail = client.get(f"/api/v1/customers/{customer_id}", headers=headers)
        assert customer_detail.status_code == 200
        assert customer_detail.json()["lead"]["id"] == lead_id
        assert customer_detail.json()["name"] == "转化后客户名"
        assert customer_detail.json()["contact_name"] == "转化后联系人"
        assert customer_detail.json()["phone"] == "13911112222"

        accountant_login = client.post(
            "/api/v1/auth/login",
            json={"username": accountant["username"], "password": "Demo@12345"},
        )
        assert accountant_login.status_code == 200
        accountant_headers = {"Authorization": f"Bearer {accountant_login.json()['access_token']}"}
        accountant_followup = client.post(
            f"/api/v1/leads/{lead_id}/followups",
            headers=accountant_headers,
            json={
                "followup_at": "2026-02-26",
                "feedback": "会计已跟进并记录",
                "notes": "测试",
            },
        )
        assert accountant_followup.status_code == 201

        unconvert_resp = client.post(f"/api/v1/leads/{lead_id}/unconvert", headers=headers, json={})
        assert unconvert_resp.status_code == 200
        assert unconvert_resp.json()["status"] in {"NEW", "FOLLOWING"}

        customers_after = client.get("/api/v1/customers", headers=headers).json()
        assert all(item["source_lead_id"] != lead_id for item in customers_after)


def test_address_resources():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        list_response = client.get("/api/v1/address-resources", headers=headers)
        assert list_response.status_code == 200

        create_response = client.post(
            "/api/v1/address-resources",
            headers=headers,
            json={
                "category": "注册地址",
                "contact_info": "微信 test001",
                "description": "支持挂靠",
                "next_action": "下周回访",
                "notes": "测试新增",
            },
        )
        assert create_response.status_code == 201
        resource_id = create_response.json()["id"]

        patch_response = client.patch(
            f"/api/v1/address-resources/{resource_id}",
            headers=headers,
            json={"next_action": "明天回访"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["next_action"] == "明天回访"


def test_billing_activities_update_amounts():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        customers_response = client.get("/api/v1/customers", headers=headers)
        assert customers_response.status_code == 200
        customer_id = customers_response.json()[0]["id"]

        create_record = client.post(
            "/api/v1/billing-records",
            headers=headers,
            json={
                "serial_no": 100,
                "customer_id": customer_id,
                "total_fee": 1000,
                "monthly_fee": 100,
                "billing_cycle_text": "测试周期",
                "due_month": "2026-12-31",
                "payment_method": "后收",
            },
        )
        assert create_record.status_code == 201
        record_id = create_record.json()["id"]

        activity_response = client.post(
            f"/api/v1/billing-records/{record_id}/activities",
            headers=headers,
            json={
                "activity_type": "PAYMENT",
                "occurred_at": "2026-02-26",
                "amount": 300,
                "payment_nature": "ONE_OFF",
                "is_prepay": False,
                "is_settlement": False,
                "content": "收到部分款项",
                "note": "测试收款",
            },
        )
        assert activity_response.status_code == 201

        reminder_with_amount = client.post(
            f"/api/v1/billing-records/{record_id}/activities",
            headers=headers,
            json={
                "activity_type": "REMINDER",
                "occurred_at": "2026-02-26",
                "amount": 200,
                "content": "催收不应填写金额",
            },
        )
        assert reminder_with_amount.status_code == 400

        records = client.get("/api/v1/billing-records", headers=headers).json()
        target = next(item for item in records if item["id"] == record_id)
        assert target["received_amount"] == 300
        assert target["outstanding_amount"] == 700
        assert target["status"] == "PARTIAL"


def test_customer_update():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        customers = client.get("/api/v1/customers", headers=headers).json()
        customer_id = customers[0]["id"]
        update_resp = client.patch(
            f"/api/v1/customers/{customer_id}",
            headers=headers,
            json={
                "name": "可编辑客户名称",
                "contact_name": "新联系人",
                "phone": "13900000000",
                "lead_notes": "更新后的备注",
            },
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["name"] == "可编辑客户名称"
        assert data["contact_name"] == "新联系人"
        assert data["phone"] == "13900000000"
        assert data["lead"]["notes"] == "更新后的备注"


def test_convert_reject_non_accountant_assignment():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_lead = client.post(
            "/api/v1/leads",
            headers=headers,
            json={
                "template_type": "FOLLOWUP",
                "name": "非会计分配测试",
                "contact_name": "王测试",
                "phone": "13800990099",
            },
        )
        assert create_lead.status_code == 201
        lead_id = create_lead.json()["id"]

        # admin 不是会计角色，应该被拒绝
        me_admin = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Demo@12345"})
        assert me_admin.status_code == 200
        admin_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {me_admin.json()['access_token']}"},
        )
        admin_id = admin_me.json()["id"]

        convert_resp = client.post(
            f"/api/v1/leads/{lead_id}/convert",
            headers=headers,
            json={"accountant_id": admin_id},
        )
        assert convert_resp.status_code == 400


def test_convert_requires_accountant_when_owner_not_accountant():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_lead = client.post(
            "/api/v1/leads",
            headers=headers,
            json={
                "template_type": "FOLLOWUP",
                "name": "必须选择会计测试",
                "contact_name": "王测试",
                "phone": "13800990100",
            },
        )
        assert create_lead.status_code == 201
        lead_id = create_lead.json()["id"]

        convert_resp = client.post(
            f"/api/v1/leads/{lead_id}/convert",
            headers=headers,
            json={},
        )
        assert convert_resp.status_code == 400


def test_user_admin_scope_owner_vs_admin():
    with TestClient(app) as client:
        owner_login = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

        owner_list = client.get("/api/v1/users", headers=owner_headers, params={"include_inactive": True})
        assert owner_list.status_code == 200
        assert all(item["role"] != "ADMIN" for item in owner_list.json())

        owner_create_accountant = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "username": "owner_created_acc",
                "password": "Demo@12345",
                "role": "ACCOUNTANT",
                "is_active": True,
            },
        )
        assert owner_create_accountant.status_code == 201

        owner_create_admin = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "username": "owner_created_admin",
                "password": "Demo@12345",
                "role": "ADMIN",
            },
        )
        assert owner_create_admin.status_code == 403

        admin_login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Demo@12345"},
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        admin_me = client.get("/api/v1/auth/me", headers=admin_headers)
        admin_id = admin_me.json()["id"]

        owner_patch_admin = client.patch(
            f"/api/v1/users/{admin_id}",
            headers=owner_headers,
            json={"is_active": False},
        )
        assert owner_patch_admin.status_code == 403

        admin_create_admin = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "username": "admin_created_admin",
                "password": "Demo@12345",
                "role": "ADMIN",
            },
        )
        assert admin_create_admin.status_code == 201


def test_user_update_self_protection():
    with TestClient(app) as client:
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Demo@12345"},
        )
        headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        me_resp = client.get("/api/v1/auth/me", headers=headers)
        me_id = me_resp.json()["id"]

        deactivate_self = client.patch(
            f"/api/v1/users/{me_id}",
            headers=headers,
            json={"is_active": False},
        )
        assert deactivate_self.status_code == 400

        change_self_role = client.patch(
            f"/api/v1/users/{me_id}",
            headers=headers,
            json={"role": "ACCOUNTANT"},
        )
        assert change_self_role.status_code == 400


def test_user_delete_flow_and_dependency_guard():
    with TestClient(app) as client:
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Demo@12345"},
        )
        headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        create_response = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "username": "delete_me",
                "password": "Demo@12345",
                "role": "ACCOUNTANT",
                "is_active": True,
            },
        )
        assert create_response.status_code == 201
        delete_id = create_response.json()["id"]

        delete_response = client.delete(f"/api/v1/users/{delete_id}", headers=headers)
        assert delete_response.status_code == 204

        list_response = client.get("/api/v1/users", headers=headers, params={"include_inactive": True})
        assert list_response.status_code == 200
        assert all(item["id"] != delete_id for item in list_response.json())

        login_deleted = client.post(
            "/api/v1/auth/login",
            json={"username": "delete_me", "password": "Demo@12345"},
        )
        assert login_deleted.status_code == 401

        create_bound_user = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "username": "bound_acc",
                "password": "Demo@12345",
                "role": "ACCOUNTANT",
                "is_active": True,
            },
        )
        assert create_bound_user.status_code == 201
        bound_user_id = create_bound_user.json()["id"]

        bound_login = client.post(
            "/api/v1/auth/login",
            json={"username": "bound_acc", "password": "Demo@12345"},
        )
        assert bound_login.status_code == 200
        bound_headers = {"Authorization": f"Bearer {bound_login.json()['access_token']}"}
        bound_lead = client.post(
            "/api/v1/leads",
            headers=bound_headers,
            json={
                "template_type": "FOLLOWUP",
                "name": "删除阻断测试线索",
                "contact_name": "联系人",
                "phone": "13800112233",
            },
        )
        assert bound_lead.status_code == 201

        blocked_delete = client.delete(f"/api/v1/users/{bound_user_id}", headers=headers)
        assert blocked_delete.status_code == 400
        assert "关联数据" in blocked_delete.json()["detail"]


def test_login_updates_last_login_and_operation_log():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["last_login_at"] is not None

        logs_response = client.get(
            "/api/v1/admin/operation-logs",
            headers=headers,
            params={"action": "LOGIN", "limit": 50},
        )
        assert logs_response.status_code == 200
        assert any(
            item["action"] == "LOGIN" and item["actor_username"] == "boss"
            for item in logs_response.json()
        )


def test_ldap_settings_permission_and_sync_guard():
    with TestClient(app) as client:
        owner_login = client.post(
            "/api/v1/auth/login",
            json={"username": "boss", "password": "Demo@12345"},
        )
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

        admin_login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Demo@12345"},
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        owner_set_admin_default = client.put(
            "/api/v1/admin/ldap/settings",
            headers=owner_headers,
            json={"default_role": "ADMIN"},
        )
        assert owner_set_admin_default.status_code == 403

        admin_update = client.put(
            "/api/v1/admin/ldap/settings",
            headers=admin_headers,
            json={
                "enabled": False,
                "server_url": "ldap://127.0.0.1:389",
                "bind_dn": "uid=admin,cn=users,dc=example,dc=com",
                "base_dn": "dc=example,dc=com",
                "user_base_dn": "cn=users,dc=example,dc=com",
                "user_filter": "(uid=*)",
                "username_attr": "uid",
                "display_name_attr": "cn",
                "default_role": "ACCOUNTANT",
            },
        )
        assert admin_update.status_code == 200

        sync_response = client.post("/api/v1/admin/ldap/sync", headers=admin_headers, json={})
        assert sync_response.status_code == 400
