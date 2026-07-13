\set ON_ERROR_STOP on

BEGIN;

INSERT INTO organization(id,name) VALUES
  ('00000000-0000-0000-0000-000000000701','Live Home Org');
INSERT INTO app_user(id,email) VALUES
  ('00000000-0000-0000-0000-000000000711','live-home@example.test');
INSERT INTO portfolio(organization_id,id,name,created_by,client_id) VALUES
  ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000721',
   'Live Portfolio','00000000-0000-0000-0000-000000000711','portfolio-client');
INSERT INTO home(organization_id,id,portfolio_id,name,created_by,client_id) VALUES
  ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000731',
   '00000000-0000-0000-0000-000000000721','Live Home',
   '00000000-0000-0000-0000-000000000711','home-client');
INSERT INTO room_type(organization_id,id,name,display_order) VALUES
  ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000741','Kitchen',9);
INSERT INTO room(organization_id,id,home_id,room_type_id,name,created_by,client_id) VALUES
  ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000751',
   '00000000-0000-0000-0000-000000000731','00000000-0000-0000-0000-000000000741',
   'Kitchen','00000000-0000-0000-0000-000000000711','room-client');
INSERT INTO asset(organization_id,id,home_id,room_id,asset_type,name,quantity,purchase_price,
                  purchase_date,tags,created_by,client_id) VALUES
  ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000761',
   '00000000-0000-0000-0000-000000000731','00000000-0000-0000-0000-000000000751',
   'Appliance','Range',2,1200.50,'2025-01-02','["kitchen"]'::jsonb,
   '00000000-0000-0000-0000-000000000711','asset-client');
INSERT INTO photo(organization_id,id,home_id,room_id,asset_id,uploader_id,client_id,purpose,
                  upload_status,original_object_key,sha256,byte_size,mime_type) VALUES
  ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000771',
   '00000000-0000-0000-0000-000000000731','00000000-0000-0000-0000-000000000751',
   '00000000-0000-0000-0000-000000000761','00000000-0000-0000-0000-000000000711',
   'document-photo','asset_document','verified',
   '00000000-0000-0000-0000-000000000701/00000000-0000-0000-0000-000000000731/originals/00000000-0000-0000-0000-000000000771.jpg',
   repeat('a',64),25,'image/jpeg');

INSERT INTO asset_document(organization_id,id,asset_id,kind,object_key) VALUES
  ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000781',
   '00000000-0000-0000-0000-000000000761','receipt',
   '00000000-0000-0000-0000-000000000701/00000000-0000-0000-0000-000000000731/originals/00000000-0000-0000-0000-000000000771.jpg');
INSERT INTO asset_document(organization_id,id,asset_id,kind,source_url) VALUES
  ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000782',
   '00000000-0000-0000-0000-000000000761','manual','https://manufacturer.example/manual.pdf');
INSERT INTO asset_research_value(
  organization_id,id,asset_id,field_name,value,provenance,source_reference,confidence,confirmed
) VALUES (
  '00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000791',
  '00000000-0000-0000-0000-000000000761','estimated_replacement_cost',
  '{"amount":"1599.00","currency":"USD"}'::jsonb,'externally_researched',
  'https://manufacturer.example/range',0.875,false
);

DO $checks$
BEGIN
  BEGIN
    INSERT INTO portfolio(organization_id,name) VALUES
      ('00000000-0000-0000-0000-000000000701','Live Portfolio');
    RAISE EXCEPTION 'portfolio name uniqueness was not enforced';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO home(organization_id,portfolio_id,name,created_by,client_id) VALUES
      ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000721',
       'Replay','00000000-0000-0000-0000-000000000711','home-client');
    RAISE EXCEPTION 'home replay uniqueness was not enforced';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO asset_document(organization_id,asset_id,kind) VALUES
      ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000761','manual');
    RAISE EXCEPTION 'asset document XOR was not enforced';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO asset_document(organization_id,asset_id,kind,object_key,source_url) VALUES
      ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000761',
       'manual','object','https://example.test');
    RAISE EXCEPTION 'asset document XOR was not enforced';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO asset_document(organization_id,asset_id,kind,source_url) VALUES
      ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000761',
       'unknown','https://example.test');
    RAISE EXCEPTION 'asset document kind was not enforced';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO asset_document(organization_id,asset_id,kind,source_url) VALUES
      ('00000000-0000-0000-0000-000000000701','00000000-0000-0000-0000-000000000761',
       'manual','https://manufacturer.example/manual.pdf');
    RAISE EXCEPTION 'duplicate document URL was not rejected';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
END $checks$;

DO $catalog$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid
    WHERE t.typname='photo_purpose' AND e.enumlabel='asset_document'
  ) THEN
    RAISE EXCEPTION 'asset_document photo purpose is missing';
  END IF;
END $catalog$;

ROLLBACK;
SELECT 'DAH-132 live home onboarding acceptance passed';
