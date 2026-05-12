import os

from fastapi.testclient import TestClient

from app.main import app

DEMO_PASSWORD = os.environ.get("BOOTSTRAP_DEMO_PASSWORD", "Daizhang#2026!")
EXTERNAL_PASSWORD = "External#2026"


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_external_user(
    client: TestClient,
    owner_headers: dict[str, str],
    *,
    username: str,
    phone: str,
    prefix: str,
) -> dict:
    response = client.post(
        "/api/v1/users",
        headers=owner_headers,
        json={
            "username": username,
            "password": EXTERNAL_PASSWORD,
            "role": "EXTERNAL_LEAD",
            "display_name": username,
            "phone": phone,
            "lead_name_prefix": prefix,
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_external_lead_user_can_only_manage_own_prefixed_leads():
    with TestClient(app) as client:
        owner_headers = _login(client, "boss", DEMO_PASSWORD)
        ext_user = _create_external_user(
            client,
            owner_headers,
            username="sec_ext_1",
            phone="17700000001",
            prefix="渠道甲",
        )
        other_ext_user = _create_external_user(
            client,
            owner_headers,
            username="sec_ext_2",
            phone="17700000002",
            prefix="渠道乙",
        )
        assert ext_user["email"] == ""
        assert ext_user["phone"] == "17700000001"
        assert ext_user["lead_name_prefix"] == "渠道甲"

        ext_headers = _login(client, "sec_ext_1", EXTERNAL_PASSWORD)
        other_ext_headers = _login(client, "sec_ext_2", EXTERNAL_PASSWORD)

        own_lead_resp = client.post(
            "/api/v1/leads",
            headers=ext_headers,
            json={
                "template_type": "CONVERSION",
                "name": "青岛示例有限公司",
                "contact_name": "王总",
                "phone": "13900000001",
                "source": "外部转介绍",
                "main_business": "注册公司",
            },
        )
        assert own_lead_resp.status_code == 201, own_lead_resp.text
        own_lead = own_lead_resp.json()
        assert own_lead["name"] == "渠道甲-青岛示例有限公司"
        assert own_lead["owner_id"] == ext_user["id"]

        other_lead_resp = client.post(
            "/api/v1/leads",
            headers=other_ext_headers,
            json={
                "template_type": "CONVERSION",
                "name": "济南示例有限公司",
                "contact_name": "李总",
                "source": "外部转介绍",
                "main_business": "代理记账",
            },
        )
        assert other_lead_resp.status_code == 201, other_lead_resp.text
        other_lead = other_lead_resp.json()
        assert other_lead["owner_id"] == other_ext_user["id"]

        list_resp = client.get("/api/v1/leads", headers=ext_headers)
        assert list_resp.status_code == 200
        lead_ids = {item["id"] for item in list_resp.json()}
        assert own_lead["id"] in lead_ids
        assert other_lead["id"] not in lead_ids

        other_detail_resp = client.get(f"/api/v1/leads/{other_lead['id']}", headers=ext_headers)
        assert other_detail_resp.status_code == 403

        edit_resp = client.patch(
            f"/api/v1/leads/{own_lead['id']}",
            headers=ext_headers,
            json={"name": "渠道甲-青岛示例有限公司", "main_business": "注册并代账"},
        )
        assert edit_resp.status_code == 200, edit_resp.text
        assert edit_resp.json()["name"] == "渠道甲-青岛示例有限公司"
        assert edit_resp.json()["main_business"] == "注册并代账"

        rename_resp = client.patch(
            f"/api/v1/leads/{own_lead['id']}",
            headers=ext_headers,
            json={"name": "青岛新示例有限公司"},
        )
        assert rename_resp.status_code == 200, rename_resp.text
        assert rename_resp.json()["name"] == "渠道甲-青岛新示例有限公司"

        forbidden_update_resp = client.patch(
            f"/api/v1/leads/{own_lead['id']}",
            headers=ext_headers,
            json={"status": "LOST"},
        )
        assert forbidden_update_resp.status_code == 403

        redevelop_resp = client.post(
            "/api/v1/leads",
            headers=ext_headers,
            json={
                "template_type": "REDEVELOP",
                "name": "老客二开不允许",
                "contact_name": "赵总",
                "source": "外部转介绍",
                "main_business": "股权变更",
            },
        )
        assert redevelop_resp.status_code == 403

        for path in [
            "/api/v1/customers",
            "/api/v1/billing-records",
            "/api/v1/todos",
            "/api/v1/address-resources",
            "/api/v1/common-library-items",
        ]:
            forbidden_resp = client.get(path, headers=ext_headers)
            assert forbidden_resp.status_code == 403, f"{path}: {forbidden_resp.status_code} {forbidden_resp.text}"

        assert client.get(f"/api/v1/leads/{own_lead['id']}/followups", headers=ext_headers).status_code == 403
        assert client.post(
            f"/api/v1/leads/{own_lead['id']}/followups",
            headers=ext_headers,
            json={"followup_at": "2026-05-12", "feedback": "外部不允许写跟进"},
        ).status_code == 403
        assert client.post(
            f"/api/v1/leads/{own_lead['id']}/convert",
            headers=ext_headers,
            json={"responsible_user_id": ext_user["id"]},
        ).status_code == 403

        owner_lead_resp = client.post(
            "/api/v1/leads",
            headers=owner_headers,
            json={
                "template_type": "CONVERSION",
                "name": "内部测试转化客户",
                "contact_name": "内部联系人",
                "source": "Sally直播",
                "main_business": "代账",
            },
        )
        assert owner_lead_resp.status_code == 201, owner_lead_resp.text
        convert_to_external_resp = client.post(
            f"/api/v1/leads/{owner_lead_resp.json()['id']}/convert",
            headers=owner_headers,
            json={"responsible_user_id": ext_user["id"]},
        )
        assert convert_to_external_resp.status_code == 400
