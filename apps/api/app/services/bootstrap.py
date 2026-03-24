from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import AddressResource, BillingActivity, BillingRecord, CommonLibraryItem, Customer, Lead, User

DEMO_USER_SPECS = (
    ("boss", "OWNER"),
    ("admin", "ADMIN"),
    ("manager", "MANAGER"),
    ("accountant", "ACCOUNTANT"),
    ("accountant2", "ACCOUNTANT"),
    ("accountant3", "ACCOUNTANT"),
    ("accountant4", "ACCOUNTANT"),
)


def bootstrap_data(db: Session) -> None:
    users = db.execute(select(User)).scalars().all()
    user_map = {user.username: user for user in users}
    demo_users_changed = False
    for username, role in DEMO_USER_SPECS:
        existing_user = user_map.get(username)
        if existing_user is None:
            db.add(
                User(
                    username=username,
                    password_hash=hash_password(settings.bootstrap_demo_password),
                    role=role,
                )
            )
            demo_users_changed = True
            continue

        if existing_user.role != role:
            existing_user.role = role
            demo_users_changed = True
        if not verify_password(settings.bootstrap_demo_password, existing_user.password_hash):
            existing_user.password_hash = hash_password(settings.bootstrap_demo_password)
            demo_users_changed = True

    if demo_users_changed:
        db.commit()
        users = db.execute(select(User)).scalars().all()
    elif not users:
        users = db.execute(select(User)).scalars().all()

    user_map = {user.username: user for user in users}
    manager_user = user_map.get("manager")
    subordinate_changed = False
    if manager_user is not None:
        for username in ("accountant2", "accountant3", "accountant4"):
            subordinate = user_map.get(username)
            if subordinate is None:
                continue
            if subordinate.manager_user_id != manager_user.id:
                subordinate.manager_user_id = manager_user.id
                subordinate_changed = True
    if subordinate_changed:
        db.commit()
        users = db.execute(select(User)).scalars().all()

    lead_exists = db.execute(select(Lead.id)).first()
    if lead_exists is None:
        owner = next((item for item in users if item.role in {"OWNER", "ADMIN"}), users[0])
        demo_leads = [
            Lead(
                template_type="FOLLOWUP",
                name="深圳示例科技有限公司",
                grade="A",
                contact_name="王总",
                phone="13800000001",
                country="跨境电商",
                service_start_text="2025.07.02",
                company_nature="外贸一般人",
                service_mode="陪跑",
                other_contact="黄广",
                main_business="多店铺，有走9810的有0110，车衣",
                intro="SALLY",
                fee_standard="9600/年",
                first_billing_period="2026.01-12",
                source="转介绍",
                status="FOLLOWING",
                next_reminder_at=date.today() + timedelta(days=3),
                reminder_value="100",
                last_feedback="已沟通代理记账报价，等待确认",
                notes="重点跟进",
                owner_id=owner.id,
            ),
            Lead(
                template_type="CONVERSION",
                name="东莞样例贸易公司",
                grade="B",
                contact_name="陈小姐",
                phone="13800000002",
                region="青岛",
                contact_start_date=date.today(),
                contact_wechat="陈小姐",
                main_business="首次联系，补充资料中",
                intro="麦总",
                reserve_2="48期",
                source="电话开发",
                status="NEW",
                next_reminder_at=date.today() + timedelta(days=1),
                last_feedback="首次联系，补充资料中",
                notes="",
                owner_id=owner.id,
            ),
            Lead(
                template_type="FOLLOWUP",
                name="安杰尔",
                grade="A",
                contact_name="安杰尔负责人",
                phone="13800000011",
                country="跨境电商",
                service_start_text="2025.01",
                company_nature="一般纳税人",
                service_mode="代账",
                source="历史客户",
                status="CONVERTED",
                owner_id=owner.id,
            ),
            Lead(
                template_type="FOLLOWUP",
                name="海恩诺",
                grade="B",
                contact_name="海恩诺负责人",
                phone="13800000012",
                status="CONVERTED",
                owner_id=owner.id,
            ),
            Lead(
                template_type="FOLLOWUP",
                name="海德和信",
                grade="B",
                contact_name="海德和信负责人",
                phone="13800000013",
                status="CONVERTED",
                owner_id=owner.id,
            ),
            Lead(
                template_type="FOLLOWUP",
                name="晟坤纺织",
                grade="C",
                contact_name="晟坤纺织负责人",
                phone="13800000014",
                status="CONVERTED",
                owner_id=owner.id,
            ),
            Lead(
                template_type="FOLLOWUP",
                name="叶荣钢铁",
                grade="C",
                contact_name="叶荣钢铁负责人",
                phone="13800000015",
                status="CONVERTED",
                owner_id=owner.id,
            ),
        ]
        db.add_all(demo_leads)
        db.commit()
        converted_leads = db.execute(select(Lead).where(Lead.status == "CONVERTED")).scalars().all()
        accountant = next((item for item in users if item.role == "ACCOUNTANT"), owner)
        for converted_lead in converted_leads:
            existing_customer = db.execute(
                select(Customer).where(Customer.source_lead_id == converted_lead.id)
            ).scalar_one_or_none()
            if existing_customer is None:
                db.add(
                    Customer(
                        name=converted_lead.name,
                        contact_name=converted_lead.contact_name,
                        phone=converted_lead.phone,
                        assigned_accountant_id=accountant.id,
                        source_lead_id=converted_lead.id,
                    )
                )
        db.commit()

    resource_exists = db.execute(select(AddressResource.id)).first()
    if resource_exists is None:
        db.add_all(
            [
                AddressResource(
                    category="自贸区",
                    contact_info="186 5320 7940 孙建云",
                    served_companies="深圳示例科技有限公司",
                    description="阎总介绍，地址 3000/年",
                    next_action="2/25 再次电话沟通",
                    notes="可作为转化线索来源",
                ),
                AddressResource(
                    category="注册地址",
                    contact_info="微信：qdzc001",
                    served_companies="东莞样例贸易公司、海德和信",
                    description="支持一般纳税人地址挂靠",
                    next_action="补充合同模板后推进",
                    notes="报价按年",
                ),
            ]
        )

    common_library_exists = db.execute(select(CommonLibraryItem.id)).first()
    if common_library_exists is None:
        db.add_all(
            [
                CommonLibraryItem(
                    module_type="TEMPLATE",
                    visibility="INTERNAL",
                    category="培训资料",
                    title="新企业培训用语",
                    content="欢迎建联后先发送基础办税、开票、报税时间要求，再提醒保存会计收件地址。",
                    notes="适合首单客户",
                ),
                CommonLibraryItem(
                    module_type="TEMPLATE",
                    visibility="INTERNAL",
                    category="催单",
                    title="每月催单用语",
                    content="请在每月 5 日前把票据和银行流水发齐，避免影响报税时效。",
                ),
                CommonLibraryItem(
                    module_type="TEMPLATE",
                    visibility="INTERNAL",
                    category="社保",
                    title="交社保催存款",
                    content="本月社保即将扣款，请提前把对应金额存入公户，避免扣款失败。",
                ),
                CommonLibraryItem(
                    module_type="DIRECTORY",
                    visibility="INTERNAL",
                    category="税局",
                    title="市南税局",
                    phone="0532-12366",
                    address="青岛市市南区示例路 18 号",
                    notes="工作日联系",
                ),
                CommonLibraryItem(
                    module_type="DIRECTORY",
                    visibility="INTERNAL",
                    category="银行",
                    title="招商银行香港中路支行",
                    phone="0532-88886666",
                    address="青岛市市南区香港中路 66 号",
                ),
                CommonLibraryItem(
                    module_type="EXTENSION_A",
                    visibility="PUBLIC",
                    category="常用语",
                    title="首单退税要求条件",
                    content="先确认备案、报关单、进项票、收汇资料齐全，再统一给客户发送清单。",
                ),
                CommonLibraryItem(
                    module_type="EXTENSION_B",
                    visibility="PUBLIC",
                    category="收件",
                    title="会计收件地址",
                    content="青岛市市南区示例大厦 12 层财税部，收件人：会计组，电话：0532-66668888。",
                ),
                CommonLibraryItem(
                    module_type="EXTENSION_C",
                    visibility="INTERNAL",
                    category="预留",
                    title="预留模块示例",
                    content="这里可后续改成新的常用资料分类。",
                ),
            ]
        )
    else:
        public_seed_titles = {
            "首单退税要求条件",
            "会计收件地址",
        }
        existing_items = db.execute(select(CommonLibraryItem)).scalars().all()
        for item in existing_items:
            if item.title in public_seed_titles:
                item.visibility = "PUBLIC"

    billing_exists = db.execute(select(BillingRecord.id)).first()
    if billing_exists is None:
        customer_map = {
            customer.name: customer
            for customer in db.execute(select(Customer)).scalars().all()
        }
        demo_records = [
            BillingRecord(
                serial_no=1,
                customer_id=customer_map["安杰尔"].id if "安杰尔" in customer_map else None,
                customer_name="安杰尔",
                total_fee=4800,
                monthly_fee=400,
                billing_cycle_text="4800/6月17收（2025.1-2025.12）",
                due_month="2025-12-31",
                payment_method="预收",
                status="CLEARED",
                received_amount=4800,
                outstanding_amount=0,
                note="400/月，年报200，退税300",
                color_tag="FF92D050",
            ),
            BillingRecord(
                serial_no=2,
                customer_id=customer_map["海恩诺"].id if "海恩诺" in customer_map else None,
                customer_name="海恩诺",
                total_fee=8400,
                monthly_fee=700,
                billing_cycle_text="2026/1月8收（2025.1-2025.12）",
                due_month="2025-12-31",
                payment_method="后收",
                status="PARTIAL",
                received_amount=5600,
                outstanding_amount=2800,
                note="记账加退税每月700，年底付",
                extra_note="10800",
                color_tag="FF00B0F0",
            ),
            BillingRecord(
                serial_no=3,
                customer_id=customer_map["海德和信"].id if "海德和信" in customer_map else None,
                customer_name="海德和信",
                total_fee=4800,
                monthly_fee=400,
                billing_cycle_text="2025/12/31收（2025.1-2025.12）",
                due_month="2025-12-31",
                payment_method="后收",
                status="FULL_ARREARS",
                received_amount=0,
                outstanding_amount=4800,
                note="账本100年报赠送，400/月含退税。",
                color_tag="FF00B0F0",
            ),
            BillingRecord(
                serial_no=4,
                customer_id=customer_map["晟坤纺织"].id if "晟坤纺织" in customer_map else None,
                customer_name="晟坤纺织",
                total_fee=2400,
                monthly_fee=200,
                billing_cycle_text="2025/2/22收（2024.1-2024.12）",
                due_month="2024-12-31",
                payment_method="后收",
                status="FULL_ARREARS",
                received_amount=0,
                outstanding_amount=2400,
                note="后付费，需催收",
                color_tag="FFFFFF00",
            ),
            BillingRecord(
                serial_no=5,
                customer_id=customer_map["叶荣钢铁"].id if "叶荣钢铁" in customer_map else None,
                customer_name="叶荣钢铁",
                total_fee=2800,
                monthly_fee=400,
                billing_cycle_text="2025/12/30收（2025.7-2025.12）",
                due_month="2025-12-31",
                payment_method="后收",
                status="PARTIAL",
                received_amount=1200,
                outstanding_amount=1600,
                note="200/月，400/月，根据业务量调整",
                color_tag="FF00B0F0",
            ),
        ]
        db.add_all(demo_records)

    db.commit()

    activity_exists = db.execute(select(BillingActivity.id)).first()
    if activity_exists is None:
        owner = next((item for item in users if item.role in {"OWNER", "ADMIN"}), users[0])
        records = db.execute(select(BillingRecord).order_by(BillingRecord.id.asc())).scalars().all()
        if records:
            activities = [
                BillingActivity(
                    billing_record_id=records[0].id,
                    activity_type="PAYMENT",
                    occurred_at=date.today() - timedelta(days=20),
                    actor_id=owner.id,
                    amount=4800,
                    payment_nature="YEARLY",
                    receipt_account="一帆光大",
                    is_prepay=True,
                    is_settlement=True,
                    content="年费一次性预收到账",
                    note="含年报和退税服务",
                ),
                BillingActivity(
                    billing_record_id=records[min(1, len(records) - 1)].id,
                    activity_type="REMINDER",
                    occurred_at=date.today() - timedelta(days=2),
                    actor_id=owner.id,
                    content="已电话催款，客户反馈月底付款",
                    next_followup_at=date.today() + timedelta(days=5),
                    note="需继续跟进",
                ),
            ]
            db.add_all(activities)
            db.commit()
