BEGIN;

-- Existing imported portfolios and homes have no application replay identity.
-- New live-onboarding writes always populate both nullable columns.
ALTER TABLE portfolio ADD COLUMN created_by uuid REFERENCES app_user(id);
ALTER TABLE portfolio ADD COLUMN client_id text;
ALTER TABLE home ADD COLUMN created_by uuid REFERENCES app_user(id);
ALTER TABLE home ADD COLUMN client_id text;

ALTER TABLE portfolio ADD CONSTRAINT portfolio_org_name_unique
  UNIQUE (organization_id,name);
CREATE UNIQUE INDEX portfolio_replay_unique
  ON portfolio(organization_id,created_by,client_id)
  WHERE created_by IS NOT NULL AND client_id IS NOT NULL;
CREATE UNIQUE INDEX home_replay_unique
  ON home(organization_id,created_by,client_id)
  WHERE created_by IS NOT NULL AND client_id IS NOT NULL;

ALTER TABLE asset_document ADD CONSTRAINT asset_document_kind_check
  CHECK (kind IN ('receipt','warranty','manual','product_page','other'));
ALTER TABLE asset_document ADD CONSTRAINT asset_document_reference_xor_check
  CHECK ((object_key IS NOT NULL AND source_url IS NULL)
      OR (object_key IS NULL AND source_url IS NOT NULL));
CREATE UNIQUE INDEX asset_document_object_unique
  ON asset_document(organization_id,asset_id,kind,object_key)
  WHERE object_key IS NOT NULL;
CREATE UNIQUE INDEX asset_document_source_unique
  ON asset_document(organization_id,asset_id,kind,source_url)
  WHERE source_url IS NOT NULL;

ALTER TYPE photo_purpose ADD VALUE IF NOT EXISTS 'asset_document';

WITH fixed_room_type(name,display_order) AS (VALUES
  ('Front Yard',11),('Back Yard',12),('Garage',13),('Deck / Patio',14),
  ('Driveway',15),('Laundry Room',16),('Office',17),('Attic',18),
  ('Storage',19),('Deck',20),('Porch',21),('Boat Deck',22),
  ('Living Room',23),('Hallway',24),('Family Room',25),('Sun Room',26),
  ('Library',27),('Theater',28),('Pantry',29),('Walk-in Closet',30)
)
INSERT INTO room_type(organization_id,name,display_order)
SELECT organization.id,fixed_room_type.name,fixed_room_type.display_order
FROM organization CROSS JOIN fixed_room_type
ON CONFLICT (organization_id,name) DO NOTHING;

COMMIT;
