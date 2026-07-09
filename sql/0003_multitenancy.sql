-- sql/0003_multitenancy.sql
-- Convert single-tenant phase-1 schema to multi-tenant.
-- All existing rows belong to ONE client: RandD Tradesmen (tenant_id = 1).
-- Verified on a copy of the live DB: row counts preserved, integrity ok, FK clean.
-- MUST be applied via a schema_migration ledger (see runner in §3.4) so it never runs twice
-- (a bare re-run errors "duplicate column name" - proven).

PRAGMA foreign_keys = OFF;
BEGIN;

CREATE TABLE IF NOT EXISTS tenant (
  tenant_id  INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  slug       TEXT NOT NULL UNIQUE,
  is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO tenant (tenant_id, name, slug)
VALUES (1, 'RandD Tradesmen', 'randd-tradesmen');

CREATE TABLE IF NOT EXISTS app_user (
  user_id           INTEGER PRIMARY KEY,
  tenant_id         INTEGER,                 -- NULL only for platform super-admin
  email             TEXT NOT NULL UNIQUE,
  password_hash     TEXT,
  is_platform_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_platform_admin IN (0,1)),
  stakeholder_id    INTEGER,
  is_active         INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
  created_at        TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (tenant_id) REFERENCES tenant(tenant_id) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (stakeholder_id) REFERENCES stakeholder(stakeholder_id) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_app_user_tenant ON app_user(tenant_id);

ALTER TABLE stakeholder        ADD COLUMN tenant_id INTEGER REFERENCES tenant(tenant_id);
ALTER TABLE stakeholder_role   ADD COLUMN tenant_id INTEGER REFERENCES tenant(tenant_id);
ALTER TABLE task               ADD COLUMN tenant_id INTEGER REFERENCES tenant(tenant_id);
ALTER TABLE work_order         ADD COLUMN tenant_id INTEGER REFERENCES tenant(tenant_id);
ALTER TABLE report             ADD COLUMN tenant_id INTEGER REFERENCES tenant(tenant_id);
ALTER TABLE inspection         ADD COLUMN tenant_id INTEGER REFERENCES tenant(tenant_id);
ALTER TABLE photo_memory       ADD COLUMN tenant_id INTEGER REFERENCES tenant(tenant_id);
ALTER TABLE maintenance_check  ADD COLUMN tenant_id INTEGER REFERENCES tenant(tenant_id);
ALTER TABLE inspection_reports ADD COLUMN tenant_id INTEGER REFERENCES tenant(tenant_id);

-- property rebuild: UNIQUE(unit_code) -> UNIQUE(tenant_id, unit_code)
CREATE TABLE property_new (
  property_id INTEGER PRIMARY KEY,
  tenant_id INTEGER NOT NULL DEFAULT 1,
  unit_code TEXT NOT NULL,
  display_name TEXT, address_line_1 TEXT, city TEXT, state_province TEXT, postal_code TEXT,
  wifi_ssid TEXT, wifi_password_ciphertext TEXT, wifi_password_secret_ref TEXT,
  door_code_ciphertext TEXT, door_code_secret_ref TEXT,
  qc_assignee_stakeholder_id INTEGER, standing_instructions TEXT, cluster_id INTEGER,
  roster_active INTEGER NOT NULL DEFAULT 1 CHECK (roster_active IN (0,1)),
  source_system TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (tenant_id, unit_code),
  FOREIGN KEY (tenant_id) REFERENCES tenant(tenant_id) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (cluster_id) REFERENCES cluster(cluster_id) ON DELETE SET NULL ON UPDATE CASCADE,
  FOREIGN KEY (qc_assignee_stakeholder_id) REFERENCES stakeholder(stakeholder_id) ON DELETE SET NULL ON UPDATE CASCADE
);
INSERT INTO property_new (
  property_id, tenant_id, unit_code, display_name, address_line_1, city, state_province,
  postal_code, wifi_ssid, wifi_password_ciphertext, wifi_password_secret_ref,
  door_code_ciphertext, door_code_secret_ref, qc_assignee_stakeholder_id,
  standing_instructions, cluster_id, roster_active, source_system, created_at, updated_at)
SELECT
  property_id, 1, unit_code, display_name, address_line_1, city, state_province,
  postal_code, wifi_ssid, wifi_password_ciphertext, wifi_password_secret_ref,
  door_code_ciphertext, door_code_secret_ref, qc_assignee_stakeholder_id,
  standing_instructions, cluster_id, roster_active, source_system, created_at, updated_at
FROM property;
DROP TABLE property;
ALTER TABLE property_new RENAME TO property;

-- cluster rebuild: UNIQUE(name) -> UNIQUE(tenant_id, name)
CREATE TABLE cluster_new (
  cluster_id INTEGER PRIMARY KEY,
  tenant_id INTEGER NOT NULL DEFAULT 1,
  name TEXT NOT NULL,
  description TEXT,
  UNIQUE (tenant_id, name),
  FOREIGN KEY (tenant_id) REFERENCES tenant(tenant_id) ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO cluster_new (cluster_id, tenant_id, name, description)
SELECT cluster_id, 1, name, description FROM cluster;
DROP TABLE cluster;
ALTER TABLE cluster_new RENAME TO cluster;

-- backfill tenant_id = 1 on the ADD COLUMN tables (property/cluster already set via SELECT)
UPDATE stakeholder        SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE stakeholder_role   SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE task               SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE work_order         SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE report             SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE inspection         SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE photo_memory       SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE maintenance_check  SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE inspection_reports SET tenant_id = 1 WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_property_tenant           ON property(tenant_id);
CREATE INDEX IF NOT EXISTS idx_task_tenant               ON task(tenant_id);
CREATE INDEX IF NOT EXISTS idx_stakeholder_tenant        ON stakeholder(tenant_id);
CREATE INDEX IF NOT EXISTS idx_work_order_tenant         ON work_order(tenant_id);
CREATE INDEX IF NOT EXISTS idx_report_tenant             ON report(tenant_id);
CREATE INDEX IF NOT EXISTS idx_cluster_tenant            ON cluster(tenant_id);
CREATE INDEX IF NOT EXISTS idx_inspection_reports_tenant ON inspection_reports(tenant_id);

COMMIT;
PRAGMA foreign_keys = ON;
