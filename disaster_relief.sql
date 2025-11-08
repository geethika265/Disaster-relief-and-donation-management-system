create database Disaster_relief2;
use disaster_relief2;
DROP TABLE IF EXISTS NGO_FocusArea, Volunteer_Skill,
  CampResourceStock, FundAllocation, AidDistribution, AssignedTo,
  Donation, Resource, NGO, GovernmentAgency, Victim, Volunteer,
  ReliefCamp, Disaster;
SET FOREIGN_KEY_CHECKS = 1;

/* ===========================================================
   CORE ENTITIES  (FKs added later via ALTER TABLE)
   =========================================================== */

CREATE TABLE Disaster (
  DisasterID  INT PRIMARY KEY,
  Type        VARCHAR(50),
  Severity    VARCHAR(20),
  StartDate   DATE,
  EndDate     DATE,
  City        VARCHAR(50),
  District    VARCHAR(50),
  State       VARCHAR(50),
  Description VARCHAR(200)
);

CREATE TABLE ReliefCamp (
  CampID                INT PRIMARY KEY,
  Name                  VARCHAR(60),
  Village               VARCHAR(60),
  Taluk                 VARCHAR(60),
  District              VARCHAR(60),
  State                 VARCHAR(60),
  Capacity              INT,
  CampStatus            VARCHAR(20),   
  OpenDate              DATE,
  CloseDate             DATE,
  DisasterID            INT NOT NULL,          -- 1:M relationship (total participation)
  InChargeVolunteerID   INT,                   -- 1:1 relationship (can be nullable initially)
  UNIQUE (InChargeVolunteerID)         
);

CREATE TABLE Volunteer (
  VolunteerID  INT PRIMARY KEY,
  Name         VARCHAR(60),
  Phone        VARCHAR(15) UNIQUE,
  Email        VARCHAR(80),
  Availability VARCHAR(20),            -- Full/Partial/OnCall
  -- Composite HomeBase
  HomeCity     VARCHAR(60),
  HomeState    VARCHAR(60),
  -- Self-recursive 1:M relationship (Volunteer supervises other Volunteers)
  SupervisorID INT                     -- FK to Volunteer(VolunteerID)
);

CREATE TABLE Victim (
  VictimID     INT PRIMARY KEY,
  Name         VARCHAR(60),
  Age          INT,
  Gender       CHAR(1),
  -- Composite Address
  Village      VARCHAR(60),
  Taluk        VARCHAR(60),
  District     VARCHAR(60),
  State        VARCHAR(60),
  VulnerabilityTag VARCHAR(60),
  FamilySize   INT,
  CampID       INT NULL               -- FK (STAYS_IN) — nullable = partial participation
);

CREATE TABLE GovernmentAgency (
  AgencyID              INT PRIMARY KEY,
  Name                  VARCHAR(80),
  Level                 VARCHAR(20),   -- Central/State/District
  ContactPhone          VARCHAR(20),
  Email                 VARCHAR(80),
  -- Composite Jurisdiction
  JurisdictionState     VARCHAR(60),
  JurisdictionDistrict  VARCHAR(60)
);

CREATE TABLE NGO (
  NGOID        INT PRIMARY KEY,
  Name         VARCHAR(80),
  RegNo        VARCHAR(30) UNIQUE,
  ContactPhone VARCHAR(20),
  Email        VARCHAR(80),
  -- Composite HQ
  HQCity       VARCHAR(60),
  HQState      VARCHAR(60),
  -- Self-recursive 1:M relationship (NGO partners with other NGOs)
  PartnerNGOID INT,                    -- FK to NGO(NGOID)
  MoUSignedOn  DATE,
  Scope        VARCHAR(120)
);

CREATE TABLE Resource (
  ResourceID    INT PRIMARY KEY,
  Category      VARCHAR(40),
  ItemName      VARCHAR(80),
  Unit          VARCHAR(20),
  ShelfLifeDays INT
);

CREATE TABLE Donation (
  DonationID INT PRIMARY KEY,
  Amount     INT,
  Mode       VARCHAR(20),   -- Online/Cheque/Cash...
  DonorType  VARCHAR(20),   -- Individual/Corporate/Govt
  Date       DATE,
  Notes      VARCHAR(120)
);

/* ===========================================================
   RELATIONSHIP / SUPPORT TABLES
   =========================================================== */

-- M:N Volunteer ⟷ Camp with descriptive attributes (From/To dates)
CREATE TABLE AssignedTo (
  CampID      INT,                    -- PK + FK
  VolunteerID INT,                    -- PK + FK
  FromDate    DATE,                   -- PK only
  ToDate      DATE,
  PRIMARY KEY (CampID, VolunteerID, FromDate)
);

-- M:N Camp ⟷ Resource with stock attributes
CREATE TABLE CampResourceStock (
  CampID       INT,                   -- PK + FK
  ResourceID   INT,                   -- PK + FK
  CurrentQty   INT,
  ReorderLevel INT,
  PRIMARY KEY (CampID, ResourceID)
);

-- CORRECTED: Weak entity AidDistribution - owned by Victim only + partial key DistDate
-- Other entities are just regular relationships (single line connections)
CREATE TABLE AidDistribution (
  VictimID           INT,             -- PK + FK (OWNER - Strong Entity) 
  DistDate           DATE,            -- PK (partial key/discriminator)
  CampID             INT,             -- FK only (regular relationship)
  ResourceID         INT,             -- FK only (regular relationship)
  Qty                INT,
  GivenByVolunteerID INT,             -- FK only (regular relationship)
  PRIMARY KEY (VictimID, DistDate)    -- Only owner + partial key
);

-- Ternary relation: Agency – NGO – Donation
CREATE TABLE FundAllocation (
  AgencyID     INT,                   -- PK + FK
  NGOID        INT,                   -- PK + FK
  DonationID   INT,                   -- PK + FK
  Purpose      VARCHAR(120),
  SanctionDate DATE,
  PRIMARY KEY (AgencyID, NGOID, DonationID)
);

-- Multivalued attribute: NGO.FocusArea
CREATE TABLE NGO_FocusArea (
  NGOID     INT,                      -- PK + FK
  FocusArea VARCHAR(40),              -- PK only
  PRIMARY KEY (NGOID, FocusArea)
);

-- Multivalued attribute: Volunteer.Skills
CREATE TABLE Volunteer_Skill (
  VolunteerID INT,                    -- PK + FK
  Skill       VARCHAR(40),            -- PK only
  PRIMARY KEY (VolunteerID, Skill)
);

/* ===========================================================
   ADD ALL FOREIGN KEYS USING ALTER TABLE
   =========================================================== */

-- 1:M BELONGS_TO (Camp → Disaster) - Total participation
ALTER TABLE ReliefCamp
  ADD CONSTRAINT fk_camp_disaster
  FOREIGN KEY (DisasterID) REFERENCES Disaster(DisasterID);

-- 1:1 IN_CHARGE (Camp ↔ Volunteer)
ALTER TABLE ReliefCamp
  ADD CONSTRAINT fk_camp_incharge_vol
  FOREIGN KEY (InChargeVolunteerID) REFERENCES Volunteer(VolunteerID);

-- Self-recursive 1:M in Volunteer table (Supervisor)
ALTER TABLE Volunteer
  ADD CONSTRAINT fk_volunteer_supervisor
  FOREIGN KEY (SupervisorID) REFERENCES Volunteer(VolunteerID);

-- 1:M STAYS_IN (Victim → Camp) - Partial participation (NULL allowed)
ALTER TABLE Victim
  ADD CONSTRAINT fk_victim_stays_in_camp
  FOREIGN KEY (CampID) REFERENCES ReliefCamp(CampID);

-- Self-recursive 1:M in NGO table (Partners)
ALTER TABLE NGO
  ADD CONSTRAINT fk_ngo_partner
  FOREIGN KEY (PartnerNGOID) REFERENCES NGO(NGOID);

-- M:N ASSIGNED_TO
ALTER TABLE AssignedTo
  ADD CONSTRAINT fk_assignedto_camp
  FOREIGN KEY (CampID) REFERENCES ReliefCamp(CampID);
ALTER TABLE AssignedTo
  ADD CONSTRAINT fk_assignedto_vol
  FOREIGN KEY (VolunteerID) REFERENCES Volunteer(VolunteerID);

-- M:N STOCKED_AT
ALTER TABLE CampResourceStock
  ADD CONSTRAINT fk_stock_camp
  FOREIGN KEY (CampID) REFERENCES ReliefCamp(CampID);
ALTER TABLE CampResourceStock
  ADD CONSTRAINT fk_stock_resource
  FOREIGN KEY (ResourceID) REFERENCES Resource(ResourceID);

-- CORRECTED: WEAK ENTITY AidDistribution - only VictimID is PK+FK, others are FK only
ALTER TABLE AidDistribution
  ADD CONSTRAINT fk_aid_victim
  FOREIGN KEY (VictimID) REFERENCES Victim(VictimID);
ALTER TABLE AidDistribution
  ADD CONSTRAINT fk_aid_camp
  FOREIGN KEY (CampID) REFERENCES ReliefCamp(CampID);
ALTER TABLE AidDistribution
  ADD CONSTRAINT fk_aid_resource
  FOREIGN KEY (ResourceID) REFERENCES Resource(ResourceID);
ALTER TABLE AidDistribution
  ADD CONSTRAINT fk_aid_givenby_vol
  FOREIGN KEY (GivenByVolunteerID) REFERENCES Volunteer(VolunteerID);

-- TERNARY: FUND_ALLOCATION
ALTER TABLE FundAllocation
  ADD CONSTRAINT fk_fund_agency
  FOREIGN KEY (AgencyID) REFERENCES GovernmentAgency(AgencyID);
ALTER TABLE FundAllocation
  ADD CONSTRAINT fk_fund_ngo
  FOREIGN KEY (NGOID) REFERENCES NGO(NGOID);
ALTER TABLE FundAllocation
  ADD CONSTRAINT fk_fund_donation
  FOREIGN KEY (DonationID) REFERENCES Donation(DonationID);

-- MULTIVALUED: NGO_FocusArea, Volunteer_Skill
ALTER TABLE NGO_FocusArea
  ADD CONSTRAINT fk_focus_ngo
  FOREIGN KEY (NGOID) REFERENCES NGO(NGOID);

ALTER TABLE Volunteer_Skill
  ADD CONSTRAINT fk_skill_vol
  FOREIGN KEY (VolunteerID) REFERENCES Volunteer(VolunteerID);
  
DESCRIBE AidDistribution;
RENAME TABLE CampResourceStock TO Stocked_At;
ALTER TABLE Victim
  DROP COLUMN VulnerabilityTag,
  DROP COLUMN FamilySize;
ALTER TABLE Volunteer
  DROP COLUMN HomeCity,
  DROP COLUMN Email,
  DROP COLUMN HomeState;
ALTER TABLE Volunteer DROP FOREIGN KEY fk_volunteer_supervisor;
ALTER TABLE Volunteer DROP COLUMN SupervisorID;
ALTER TABLE GovernmentAgency
  DROP COLUMN JurisdictionState,
  DROP COLUMN Email;
  
  
ALTER TABLE Disaster
  DROP COLUMN Description;
ALTER TABLE ReliefCamp
  DROP FOREIGN KEY fk_camp_incharge_vol;   -- remove the constraint
ALTER TABLE ReliefCamp
  DROP COLUMN InChargeVolunteerID;         -- remove the column

CREATE TABLE InCharge (
  CampID      INT PRIMARY KEY,              -- each camp appears once
  VolunteerID INT UNIQUE,                   -- each volunteer can be in-charge of at most one camp
  FOREIGN KEY (CampID) REFERENCES ReliefCamp(CampID),
  FOREIGN KEY (VolunteerID) REFERENCES Volunteer(VolunteerID)
);
ALTER TABLE GovernmentAgency
  CHANGE COLUMN ContactPhone Contact VARCHAR(20),
  CHANGE COLUMN JurisdictionDistrict Jurisdiction VARCHAR(60);
ALTER TABLE NGO
  DROP COLUMN HQState,
  DROP COLUMN Email,
  DROP COLUMN MoUSignedOn,
  DROP COLUMN Scope,
  DROP COLUMN HQCity;
ALTER TABLE NGO
  CHANGE COLUMN ContactPhone Contact VARCHAR(20);
ALTER TABLE FundAllocation
  DROP COLUMN SanctionDate;

-- 1) Rename FromDate → Date
ALTER TABLE AssignedTo
  CHANGE COLUMN FromDate Date DATE;

-- 2) Drop ToDate
ALTER TABLE AssignedTo
  DROP COLUMN ToDate;

-- 3) Rebuild the PRIMARY KEY to use (CampID, VolunteerID, Date)
ALTER TABLE AssignedTo
  DROP PRIMARY KEY;

ALTER TABLE AssignedTo
  ADD PRIMARY KEY (CampID, VolunteerID, Date);
DESCRIBE AssignedTo;



/* Disaster */
INSERT INTO Disaster (DisasterID, Type, Severity, StartDate, EndDate, City, District, State)
VALUES
(1, 'Flood', 'Severe', '2024-07-01', '2024-07-20', 'Chennai', 'Chennai', 'Tamil Nadu'),
(2, 'Earthquake', 'High', '2024-05-15', '2024-05-16', 'Bhuj', 'Kutch', 'Gujarat'),
(3, 'Cyclone', 'Moderate', '2024-08-05', '2024-08-12', 'Puri', 'Puri', 'Odisha');

/* ReliefCamp */
INSERT INTO ReliefCamp (CampID, Name, Village, Taluk, District, State, Capacity, CampStatus, OpenDate, CloseDate, DisasterID)
VALUES
(101, 'Camp A', 'Velachery', 'Chennai South', 'Chennai', 'Tamil Nadu', 200, 'Active', '2024-07-02', NULL, 1),
(102, 'Camp B', 'Bhuj East', 'Bhuj', 'Kutch', 'Gujarat', 150, 'Closed', '2024-05-15', '2024-05-30', 2),
(103, 'Camp C', 'Konark', 'Puri', 'Puri', 'Odisha', 300, 'Active', '2024-08-06', NULL, 3);

/* Volunteer */
INSERT INTO Volunteer (VolunteerID, Name, Phone, Availability)
VALUES
(201, 'Ravi Kumar', '9000011111', 'Full'),
(202, 'Asha Mehta', '9000022222', 'OnCall'),
(203, 'Imran Ali', '9000033333', 'Partial'),
(204, 'Sunita Rao', '9000044444', 'Full');

/* Volunteer_Skill */
INSERT INTO Volunteer_Skill (VolunteerID, Skill)
VALUES
(201, 'FirstAid'),
(201, 'Logistics'),
(202, 'Cooking'),
(203, 'Nursing'),
(204, 'Rescue');

/* Victim */
INSERT INTO Victim (VictimID, Name, Age, Gender, Village, Taluk, District, State, CampID)
VALUES
(301, 'Karthik', 35, 'M', 'Velachery', 'Chennai South', 'Chennai', 'Tamil Nadu', 101),
(302, 'Lakshmi', 40, 'F', 'Velachery', 'Chennai South', 'Chennai', 'Tamil Nadu', 101),
(303, 'Rajesh', 50, 'M', 'Bhuj East', 'Bhuj', 'Kutch', 'Gujarat', 102),
(304, 'Seema', 28, 'F', 'Konark', 'Puri', 'Puri', 'Odisha', 103);

/* Resource */
INSERT INTO Resource (ResourceID, Category, ItemName, Unit)
VALUES
(401, 'Food', 'Rice Bag', 'kg'),
(402, 'Medical', 'FirstAid Kit', 'box'),
(403, 'Shelter', 'Tent', 'unit'),
(404, 'Clothing', 'Blanket', 'piece');

/* Stocked_At */
INSERT INTO Stocked_At (CampID, ResourceID, CurrentQty, ReorderLevel)
VALUES
(101, 401, 500, 100),
(101, 402, 50, 10),
(102, 403, 30, 5),
(103, 404, 200, 50);

/* AidDistribution */
INSERT INTO AidDistribution (VictimID, DistDate, CampID, ResourceID, Qty, GivenByVolunteerID)
VALUES
(301, '2024-07-05', 101, 401, 10, 201),
(302, '2024-07-05', 101, 402, 1, 202),
(303, '2024-05-16', 102, 403, 1, 203),
(304, '2024-08-07', 103, 404, 2, 204);

/* AssignedTo */
INSERT INTO AssignedTo (CampID, VolunteerID, Date)
VALUES
(101, 201, '2024-07-02'),
(101, 202, '2024-07-03'),
(102, 203, '2024-05-15'),
(103, 204, '2024-08-06');

/* InCharge */
INSERT INTO InCharge (CampID, VolunteerID)
VALUES
(101, 201),
(102, 203),
(103, 204);

/* GovernmentAgency */
INSERT INTO GovernmentAgency (AgencyID, Name, Level, Contact, Jurisdiction)
VALUES
(501, 'NDMA', 'Central', '011-1111111', 'All India'),
(502, 'Gujarat Relief Board', 'State', '079-2222222', 'Gujarat'),
(503, 'Odisha Disaster Dept', 'State', '0674-3333333', 'Odisha');

/* NGO */
INSERT INTO NGO (NGOID, Name, RegNo, Contact, PartnerNGOID)
VALUES
(601, 'Helping Hands', 'NGO001', '080-4444444', NULL),
(602, 'Relief Trust', 'NGO002', '080-5555555', 601),
(603, 'Care Foundation', 'NGO003', '080-6666666', NULL);

/* NGO_FocusArea */
INSERT INTO NGO_FocusArea (NGOID, FocusArea)
VALUES
(601, 'Food'),
(601, 'Shelter'),
(602, 'Medical'),
(603, 'Rescue');

/* Donation */
INSERT INTO Donation (DonationID, Amount, Mode, DonorType, Date)
VALUES
(701, 500000, 'Online', 'Corporate', '2024-07-03'),
(702, 200000, 'Cheque', 'Individual', '2024-05-16'),
(703, 300000, 'Cash', 'Government', '2024-08-08');

/* FundAllocation */
INSERT INTO FundAllocation (AgencyID, NGOID, DonationID, Purpose)
VALUES
(501, 601, 701, 'Food distribution'),
(502, 602, 702, 'Medical kits'),
(503, 603, 703, 'Shelter materials');

DROP TABLE IF EXISTS InCharge;

DROP TABLE IF EXISTS AidDistribution;

CREATE TABLE AidDistribution (
  VolunteerID INT,   -- PK + FK (owner 1)
  VictimID    INT,   -- PK + FK (owner 2)
  ResourceID  INT,   -- PK + FK (owner 3)
  DistDate    DATE,  -- PK only (partial key)
  Qty         INT CHECK (Qty > 0),
  PRIMARY KEY (VolunteerID, VictimID, ResourceID, DistDate),

  FOREIGN KEY (VolunteerID) REFERENCES Volunteer(VolunteerID),
  FOREIGN KEY (VictimID)    REFERENCES Victim(VictimID),
  FOREIGN KEY (ResourceID)  REFERENCES Resource(ResourceID)
);



drop procedure RegisterVictim;




DELIMITER $$
CREATE TRIGGER bi_aiddist_check
BEFORE INSERT ON AidDistribution
FOR EACH ROW
BEGIN
  -- Ensure quantity is positive
  IF NEW.Qty IS NULL OR NEW.Qty <= 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Invalid quantity: must be greater than zero';
  END IF;

  -- Ensure volunteer, victim, and resource exist
  IF NOT EXISTS (SELECT 1 FROM Volunteer WHERE VolunteerID = NEW.VolunteerID) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Volunteer ID does not exist';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM Victim WHERE VictimID = NEW.VictimID) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Victim ID does not exist';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM Resource WHERE ResourceID = NEW.ResourceID) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Resource ID does not exist';
  END IF;
END$$
DELIMITER ;

DELIMITER $$
CREATE TRIGGER ai_aiddist_decrement
AFTER INSERT ON AidDistribution
FOR EACH ROW
BEGIN
  DECLARE vCampID INT;

  -- Get the camp ID of the victim
  SELECT CampID INTO vCampID
  FROM Victim
  WHERE VictimID = NEW.VictimID;

  -- Reduce stock of the distributed resource in that camp
  UPDATE Stocked_At
  SET CurrentQty = CurrentQty - NEW.Qty
  WHERE CampID = vCampID AND ResourceID = NEW.ResourceID;

  -- Prevent stock from going below zero
  IF (SELECT CurrentQty FROM Stocked_At 
      WHERE CampID = vCampID AND ResourceID = NEW.ResourceID) < 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Stock level cannot be negative after distribution';
  END IF;
END$$
DELIMITER ;



DELIMITER $$
CREATE TRIGGER ad_aiddist_restock
AFTER DELETE ON AidDistribution
FOR EACH ROW
BEGIN
  DECLARE vCampID INT;

  -- Get the camp ID of the deleted victim’s record
  SELECT CampID INTO vCampID
  FROM Victim
  WHERE VictimID = OLD.VictimID;

  -- Restore the deleted aid quantity back to stock
  UPDATE Stocked_At
  SET CurrentQty = CurrentQty + OLD.Qty
  WHERE CampID = vCampID AND ResourceID = OLD.ResourceID;
END$$
DELIMITER ;







USE Disaster_relief2;

DROP FUNCTION IF EXISTS camp_occupancy_for;

DELIMITER $$

CREATE FUNCTION camp_occupancy_for(pCampID INT)
RETURNS DECIMAL(6,2)
READS SQL DATA DETERMINISTIC
BEGIN
  DECLARE vCap INT;
  DECLARE vCnt INT;
  DECLARE vPct DECIMAL(6,2);

  SELECT Capacity INTO vCap FROM ReliefCamp WHERE CampID = pCampID;
  SELECT COUNT(*) INTO vCnt FROM Victim WHERE CampID = pCampID;

  IF vCap IS NULL OR vCap = 0 THEN
    SET vPct = 0.00;
  ELSE
    SET vPct = ROUND((vCnt * 100.0) / vCap, 2);
  END IF;

  RETURN vPct;
END$$

DELIMITER ;


SELECT 
  CampID,
  Name,
  camp_occupancy_for(CampID) AS OccupancyPercent
FROM ReliefCamp;






