from sqlalchemy import MetaData, Table, Column, Integer, String, Boolean, ForeignKey

metadata = MetaData()

tenants_tenant = Table(
    "tenants_tenant",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("slug", String),
    Column("is_active", Boolean),
)

apis_api = Table(
    "apis_api",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", Integer, ForeignKey("tenants_tenant.id")),
    Column("slug", String),
    Column("upstream_base_url", String),
    Column("is_active", Boolean),
)

billing_plan = Table(
    "billing_plan",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("requests_per_minute", Integer),
    Column("requests_per_month", Integer),
    Column("is_active", Boolean),
)

apis_client = Table(
    "apis_client",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", Integer, ForeignKey("tenants_tenant.id")),
    Column("plan_id", Integer, ForeignKey("billing_plan.id")),
    Column("client_id", String),
)

apis_apikey = Table(
    "apis_apikey",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", Integer, ForeignKey("tenants_tenant.id")),
    Column("plan_id", Integer, ForeignKey("billing_plan.id")),
    Column("hashed_key", String),
    Column("is_active", Boolean),
)
