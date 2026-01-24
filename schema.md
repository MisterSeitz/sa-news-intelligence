# Overview of Tables and Columns

Below is a concise, schema-by-schema overview of tables and key columns for the requested schemas. For brevity, I list columns compactly; let me know if you want constraints, indexes, or full foreign keys per table expanded.  
---

## geo\_intelligence

* locations  
  * id (uuid, PK), name (text, unique), address, city, country, type, geog (geography), google\_place\_id, importance\_score (int), created\_at (timestamptz), geom (geography), province, lat (float8), long (float8), metadata (jsonb), timezone, location\_quality (int), last\_geocoded\_at, centroid\_lat (float8), centroid\_lon (float8), geocoding\_source  
* location\_links  
  * location\_id (uuid, PK part, FK locations.id), entity\_id (uuid, PK part), entity\_type (text, PK part), schema\_origin (text), metadata (jsonb)  
* jurisdictions  
  * id (uuid, PK), name (text), type (text), parent\_jurisdiction\_id (uuid), geom (geometry), metadata (jsonb), created\_at (timestamptz)  
* cities  
  * id (uuid, PK), municipality\_mdb\_code (text, FK municipalities.code), name (text), type (text), created\_at (timestamptz)  
* voting\_districts  
  * id (uuid, PK), municipality\_code (text), ward\_number (int), vd\_number (text), station\_name, registered\_voters (int), is\_split\_vd (bool), ward\_id (text), created\_at (timestamptz), geom (geometry), geocoded\_address, official\_address  
* provinces  
  * id (uuid, PK), name (text, unique), code (text, unique), geom (geometry), created\_at (timestamptz)  
* wards  
  * id (uuid, PK), ward\_code (text, unique), municipality\_id (uuid, FK), geom (geometry), created\_at (timestamptz), name, councillor\_email, councillor\_phone, councillor\_image\_url, municipality\_name, political\_party, councillor\_name, councillor\_person\_id (uuid), municipality\_mdb\_code, ward\_number (int), municipality\_code (text), map\_image\_url, party\_id (uuid), subcouncil\_id (uuid), subcouncil\_name (text), is\_coastal (bool), area\_sq\_km (real), perimeter\_km (real), centroid\_lat (real), centroid\_lng (real), compactness\_score (real), bbox\_min\_lat (real), bbox\_max\_lat, bbox\_min\_lng, bbox\_max\_lng, is\_landlocked (bool), region\_id (uuid)  
* coastlines  
  * id (uuid, PK), name (text), source (text), geom (geometry), metadata (jsonb), created\_at (timestamptz)  
* regions  
  * id (uuid, PK), name (text), code (text), municipality\_code (text), description (text), created\_at (timestamp)  
* suburbs  
  * id (uuid, PK), name (text), region\_id (uuid, FK), ward\_code (text), municipality\_code (text), geom (jsonb), created\_at (timestamp)

---

## gov\_intelligence

* parties  
  * id (uuid, PK), name (text), abbreviation, logo\_url, founded\_date, location\_id (uuid, FK geo.locations), created\_at (timestamptz), color, manifesto\_url, website\_url, description, wikipedia\_url, twitter\_url, leader, secretary\_general, headquarters, ideology, political\_position, slogan, national\_assembly\_seats (int), ncop\_seats (int), updated\_at (timestamptz)  
* memberships  
  * id (uuid, PK), person\_id (uuid, FK people.master\_identities), party\_id (uuid, FK parties.id), role, start\_date, end\_date, is\_active (bool), house  
* policies  
  * id (uuid, PK), title (text), status, reference\_number, summary, impact\_level, metadata (jsonb), created\_at (timestamptz), description, level, municipality\_code, institution\_id (uuid), document\_url, effective\_date  
* committees  
  * id (uuid, PK), name (text), house, type, province, contact\_details (jsonb), created\_at (timestamptz), municipality\_code, description, chairperson\_id (uuid)  
* legislation  
  * id (uuid, PK), title (text), bill\_number, type, status, introduction\_date, sector, summary, full\_text\_url, created\_at (timestamptz)  
* meetings  
  * id (uuid, PK), committee\_id (uuid, FK committees.id), date (timestamptz), title, summary, location, type, is\_online (bool), agenda\_url, minutes\_url, video\_url, status, municipality\_code  
* clusters  
  * id (int, PK), name (text, unique), description  
* institutions  
  * id (uuid, PK), name (text), institution\_type (text), parent\_id (uuid), cluster\_id (int, FK clusters.id), website\_url, contact\_email, contact\_phone, search\_vector (tsvector), created\_at, updated\_at, physical\_address, postal\_address, legacy\_id (int, unique), province, mec\_name, hod\_name, audit\_outcome\_2023, audit\_outcome\_2022, source\_url, last\_scraped\_at  
* municipalities  
  * id (uuid, PK), name (text), code (text, unique), province\_id (uuid, FK geo.provinces.id), geom (geometry), created\_at, legacy\_id (bigint, unique), legacy\_url, physical\_address, contact\_email, mdb\_code, postal\_address, type, area\_sq\_km (numeric), last\_scraped\_at, visita\_url, contact\_phone, district\_name, district\_code, municipal\_manager, website\_url, mayor\_name, mayor\_person\_id (uuid, FK people.master\_identities), speaker\_name, cfo\_name, logo\_url, map\_image\_url, audit\_outcome\_2023, audit\_outcome\_2022, population\_2016 (int), councillors\_page\_url, last\_enriched\_at, deputy\_mayor\_name, chief\_whip\_name, spokesperson\_name, council\_composition, controlling\_party, facebook\_url, senior\_management (jsonb), service\_queries (jsonb), provides\_water (bool), provides\_electricity (bool), provides\_sanitation (bool), provides\_waste (bool)  
* service\_contacts  
  * id (uuid, PK), municipality\_code (text, FK municipalities.code), category\_slug, contact\_email, contact\_phone, instructions, source\_url, verified\_at, created\_at, updated\_at  
* elections  
  * id (uuid, PK), election\_type (local/provincial/national), election\_date, registration\_deadline, nomination\_deadline, status, description, created\_at, updated\_at  
* candidates  
  * id (uuid, PK), election\_id (uuid, FK elections.id), person\_id (uuid, FK people.master\_identities), party\_id (uuid, FK parties.id), ward\_code, municipality\_code, candidate\_type, ballot\_position (int), is\_incumbent (bool), campaign\_slogan, campaign\_issues (jsonb), source\_url, is\_winner (bool), votes\_received (int), created\_at, updated\_at  
* election\_news  
  * id (uuid, PK), title, summary, content, source\_url (unique), source\_name, published\_at, scraped\_at, mentioned\_candidates (uuid\[\]), mentioned\_parties (uuid\[\]), ward\_codes (text\[\]), municipality\_codes (text\[\]), sentiment, topics (text\[\]), ai\_summary, is\_processed (bool), processing\_error, created\_at, scope, image\_url, priority (int)  
* transitions  
  * id (uuid, PK), election\_id (uuid, FK elections.id), ward\_code, outgoing\_person\_id (uuid), outgoing\_name, outgoing\_party, outgoing\_party\_id (uuid), outgoing\_term\_start, outgoing\_term\_end, outgoing\_performance\_score, incoming\_person\_id (uuid), incoming\_name, incoming\_party, incoming\_party\_id (uuid), incoming\_term\_start, transition\_date, handover\_status, is\_party\_change (bool, generated), notes, created\_at, updated\_at  
* election\_results  
  * id (uuid, PK), election\_id (uuid, FK), ward\_code (text, FK geo.wards), voting\_district\_id (uuid, FK geo.voting\_districts), party\_id (uuid, FK parties), party\_votes (int), registered\_voters (int), votes\_cast (int), spoilt\_ballots (int), voter\_turnout (numeric), is\_final (bool), source\_url, created\_at  
* officials  
  * id (uuid, PK), person\_id (uuid, FK people.master\_identities), municipality\_code (text, FK municipalities.code), position\_type, ward\_code (text, FK geo.wards), party\_id (uuid, FK parties), is\_current (bool), term\_start, term\_end, election\_id (uuid, FK elections), scraped\_name, scraped\_email, scraped\_phone, scraped\_image\_url, scraped\_party, source\_url, last\_scraped\_at, created\_at, updated\_at, region\_id (uuid, FK geo.regions)

---

## business\_intelligence

* tenders  
  * id (uuid, PK), tender\_number (text, unique), title, description, issuing\_entity, province, estimated\_value (numeric), date\_published, date\_closing, status, created\_at, bid\_window\_days (int, generated), document\_integrity\_hash, source\_name, source\_url, external\_reference\_id, last\_checked\_at, raw\_content\_hash, analysis\_count (int), raw\_content, updated\_at  
* awards  
  * id (uuid, PK), tender\_id (uuid, FK), org\_id (uuid), award\_amount (numeric), award\_date (date), red\_flags (text\[\]), created\_at, price\_deviation\_percent (float8), director\_conflict\_flag (bool), sub\_contracting\_percent (float8), winning\_org\_name  
* organizations  
  * id (uuid, PK), registered\_name (text, unique), reg\_number (text, unique), type, address, metadata (jsonb), created\_at, npo\_registration\_number, pbo\_status (bool), impact\_ratio (float8), beneficial\_owner\_id (uuid, FK people.master\_identities), risk\_score (float8), bbbee\_level (int), tax\_compliance\_status, csd\_number  
* relationships  
  * id (uuid, PK), person\_id (uuid, FK people.master\_identities), organization\_id (uuid, FK organizations), role, start\_date, end\_date, metadata (jsonb), created\_at, appointment\_velocity (int)  
* directory\_listings  
  * id (uuid, PK), title, description, category, tags (text\[\]), address, google\_place\_id (unique), latitude\_deprecated (float8), longitude (float8), geom (geometry), municipality\_code, ward\_code (varchar), phone, email, website, is\_claimed (bool), owner\_id (uuid), source, original\_data (jsonb), created\_at, social\_metadata (jsonb), rating (numeric), review\_count (int), opening\_hours\_raw (jsonb), image\_url, status, institution\_id (uuid), business\_name, formatted\_address, geom\_deprecated (geometry), avg\_rating (numeric), place\_types (jsonb), reviews (jsonb), opening\_hours (jsonb), website\_url, summary, photo\_metadata (jsonb), icon\_url, icon\_bg\_color, source\_imported\_at, raw\_response (jsonb), google\_check (bool), accepts\_shukrands (bool), is\_active (bool), is\_verified (bool), category\_id (uuid, FK), updated\_at, region\_id (uuid, FK)  
* entities  
  * id (uuid, PK), entity\_type (enum business/government/community), title, slug (unique), description, summary, phone, email, website, address, formatted\_address, latitude (float8), longitude (float8), geom (geometry), image\_url, icon\_url, icon\_bg\_color, photo\_metadata (jsonb), primary\_category, tags (text\[\]), status, is\_verified (bool), is\_claimed (bool), rating (numeric), review\_count (int), owner\_id (uuid, FK auth.users), claimed\_at, source, external\_id, opening\_hours (jsonb), institution\_type, services\_offered (text\[\]), community\_type, accessibility\_info (jsonb), metadata (jsonb), created\_at, updated\_at, has\_voting\_station (bool), search\_vector (tsvector)  
* entity\_place\_links  
  * id (uuid, PK), entity\_id (uuid, FK entities), place\_type (enum), place\_code (text), place\_name (text), is\_primary (bool), link\_source (text), confidence\_score (numeric), created\_at  
* categories  
  * id (uuid, PK), name (text, unique), slug (text, unique), description, entity\_types (enum\[\]), parent\_category\_id (uuid), icon, color, display\_order (int), is\_active (bool), created\_at, level (int), google\_place\_types (text\[\])  
* directory\_categories\_junction  
  * entity\_id (uuid, PK part, FK entities), category\_id (uuid, PK part, FK categories), is\_primary (bool), created\_at  
* tender\_analyses  
  * id (uuid, PK), tender\_id (uuid, unique, FK), user\_id (uuid, FK auth.users), analysis\_json (jsonb), risk\_score (int), is\_compliant (bool), ai\_model (varchar), ai\_tier (varchar), prompt\_hash (varchar), token\_usage (int), version (int), previous\_analysis\_id (uuid, FK self), created\_at, generated\_at, summary, required\_trades (text\[\]), unbundling\_potential (bool), analyzed\_at, model\_used  
* tender\_analysis\_usage  
  * id (uuid, PK), user\_id (uuid, FK auth.users), analysis\_id (uuid, FK tender\_analyses), analyzed\_at, cost\_cents (int), tender\_title (varchar), analysis\_duration\_ms (int)  
* stores  
  * id (uuid, PK), owner\_id (uuid), created\_at, opening\_hours (jsonb), seo\_metadata (jsonb), social\_links (jsonb), bio, logo\_url, banner\_url, url\_slug (unique), pickup\_address (jsonb), return\_policy, terms\_and\_conditions, commission\_type, commission\_flat\_amount (numeric), onboarding\_step (int), onboarding\_completed\_at, tier, store\_name, selling\_ward\_code, directory\_listing\_id (uuid, unique, FK directory\_listings), trade\_tags (text\[\]), slug (unique), description, logo, cover\_image, home\_ward\_code, category, is\_verified (bool), paystack\_subaccount\_code, commission\_percentage (real), updated\_at, is\_active (bool), currency  
* products  
  * id (uuid, PK), store\_id (uuid, FK stores), created\_at, catalog\_mode (bool), hide\_price (bool), is\_digital (bool), download\_files (jsonb), download\_limit (int), download\_expiry\_days (int), sku, category, low\_stock\_threshold (int), allow\_backorder (bool), title, description, price (numeric), images (text\[\]), stock\_level (int), updated\_at, is\_national (bool), ward\_code, is\_active (bool)  
* orders  
  * id (uuid, PK), store\_id (uuid, FK stores), created\_at, customer\_id (uuid, FK public.profiles), total\_amount (int), status, payment\_method, paystack\_reference, payment\_data (jsonb), shipping\_address (jsonb), updated\_at  
* order\_items  
  * id (uuid, PK), order\_id (uuid, FK orders), product\_id (uuid, FK products), quantity (int), price\_at\_purchase (int), created\_at  
* shipping\_zones  
  * id (uuid, PK), store\_id (uuid, FK stores), name, zone\_type, area\_codes (text\[\]), enabled (bool), created\_at, updated\_at  
* shipping\_methods  
  * id (uuid, PK), zone\_id (uuid, FK shipping\_zones), name, method\_type, cost (numeric), free\_shipping\_threshold (numeric), estimated\_days\_min (int), estimated\_days\_max (int), courier\_provider, courier\_config (jsonb), enabled (bool), created\_at, updated\_at  
* shipments  
  * id (uuid, PK), order\_id (uuid, FK orders), status, provider, tracking\_number, tracking\_url, shipped\_at, delivered\_at, received\_at, notes, created\_at, updated\_at  
* shipment\_updates  
  * id (uuid, PK), shipment\_id (uuid, FK shipments), status, location, notes, created\_at  
* withdrawal\_requests  
  * id (uuid, PK), store\_id (uuid, FK stores), amount (numeric), status, payment\_method, bank\_details (jsonb), requested\_at, processed\_at, processed\_by (uuid, FK public.profiles), notes, rejection\_reason, created\_at  
* refund\_requests  
  * id (uuid, PK), order\_id (uuid, FK orders), store\_id (uuid, FK stores), customer\_id (uuid, FK public.profiles), amount (numeric), reason, status, refund\_items (jsonb), admin\_notes, processed\_at, processed\_by (uuid, FK public.profiles), created\_at  
* services  
  * id (uuid, PK), slug (text, unique), name, description, price\_monthly (numeric), currency, is\_active (bool), created\_at, interval, features (jsonb)  
* subscriptions  
  * id (uuid, PK), store\_id (uuid, FK stores), service\_id (uuid, FK services), status, current\_period\_end, paystack\_subscription\_code, created\_at, updated\_at  
* ad\_placements  
  * id (uuid, PK), slug (unique), name, description, max\_ads (int), is\_active (bool), created\_at  
* advertisements  
  * id (uuid, PK), store\_id (uuid, FK stores), placement\_id (uuid, FK ad\_placements), title, description, image\_url, cta\_text, cta\_url, target\_ward\_codes (text\[\]), is\_national (bool), status, rejection\_reason, start\_date, end\_date, impressions (int), clicks (int), created\_at, updated\_at  
* ad\_defaults  
  * id (uuid, PK), placement\_id (uuid, FK ad\_placements), title, description, image\_url, cta\_text, cta\_url, priority (int), is\_active (bool), created\_at  
* customer\_relationships  
  * id (uuid, PK), store\_id (uuid, FK stores), customer\_id (uuid, FK public.profiles), tags (jsonb), notes, last\_interaction\_at, created\_at, updated\_at  
* api\_keys  
  * id (uuid, PK), user\_id (uuid, FK auth.users), key\_hash (unique), key\_prefix, name, permissions (text\[\]), rate\_limit\_tier, paystack\_subscription\_code, is\_active (bool), last\_used\_at, created\_at, expires\_at, paystack\_customer\_code, billing\_email  
* api\_usage  
  * id (uuid, PK), api\_key\_id (uuid, FK api\_keys), endpoint, method, status\_code (int), requests (int), period (date), created\_at  
* rate\_limit\_tiers  
  * tier (text, PK), requests\_per\_month (int), requests\_per\_minute (int), price\_zar (int), description  
* voting\_station\_entities  
  * id (uuid, PK), entity\_id (uuid, FK entities), voting\_district\_id (uuid, FK geo.voting\_districts), is\_primary\_venue (bool), link\_source, confidence\_score (numeric), created\_at  
* org\_canon\_map  
  * legacy\_schema (text, PK part), legacy\_table (text, PK part), legacy\_id (uuid, PK part), canonical\_entity\_id (uuid, FK entities), method, confidence (numeric), reviewed (bool), created\_at

---

## people\_intelligence

* master\_identities  
  * id (uuid, PK), full\_name, type, aliases (text\[\]), date\_of\_birth, location\_id (uuid, FK geo.locations), created\_at, gender, profile\_image\_url, contact\_details (jsonb), metadata (jsonb), is\_deceased (bool), date\_of\_death, cause\_of\_death, role, associated\_org\_id (uuid), source\_file, age (int), canonical\_name, primary\_contact, contact\_verified (bool), nationality\_code, last\_seen\_at, data\_sources\_count (int), name\_tsv (tsvector), social\_media\_handles (jsonb), pep\_tier (int), sanctions\_status (bool), risk\_score (int), last\_scanned\_at, auth\_user\_id (uuid, unique, FK auth.users), user\_id (uuid, unique, FK auth.users), email, phone, previous\_phone (jsonb), other\_nationality, person\_title  
* classification\_types  
  * id (uuid, PK), name (text, unique), description, risk\_level (int)  
* person\_classifications  
  * id (uuid, PK), person\_id (uuid, FK master\_identities), classification\_id (uuid, FK classification\_types), start\_date, end\_date, metadata (jsonb), created\_at, classification\_confidence (numeric)  
* person\_roles  
  * person\_id (uuid, PK part, FK master\_identities), role\_id (int, PK part, FK platform\_roles), assigned\_at  
* platform\_roles  
  * id (int, PK), name (text, unique), description  
* platform\_permissions  
  * id (int, PK), slug (text, unique), description  
* role\_permissions  
  * role\_id (int, PK part, FK platform\_roles), permission\_id (int, PK part, FK platform\_permissions)  
* investigation\_logs  
  * id (uuid, PK), target\_id (uuid, FK master\_identities), scan\_date, findings\_summary, source\_agent  
* mortality\_reports  
  * id (uuid, PK), person\_id (uuid, FK master\_identities), incident\_id (uuid, FK crime.incidents), method\_of\_death, location\_of\_death (uuid, FK geo.locations), verified\_by\_source, metadata (jsonb), created\_at

---

## crime\_intelligence

* incidents  
  * id (uuid, PK), type, description, city, incident\_date (timestamptz), location\_id (uuid, FK geo.locations), severity\_level (int), geom (geometry), crime\_category, summary, location, suspects\_count (int), seized\_items (jsonb), syndicate\_link, ingested\_at, status, full\_text, published\_at (date), title, source\_url (unique), occurred\_at (timestamptz), modus\_operandi\_vector (vector), weather\_condition, lighting\_condition, hour\_of\_day (generated int), day\_of\_week (generated text), moon\_phase, source\_name, crime\_subcategory, modus\_operandi, tags (text\[\]), created\_at, ward\_code, municipality\_id (bigint, FK gov.municipalities.legacy\_id), latitude (float8), longitude (float8)  
* suspect\_links  
  * incident\_id (uuid, FK incidents), person\_id (uuid, FK people.master\_identities), org\_id (uuid), involvement\_type, syndicate\_id (uuid, FK syndicates)  
* person\_status  
  * id (uuid, PK), person\_id (uuid, FK people.master\_identities), status\_type, reason, issuing\_authority, date\_issued, reward\_amount\_zar (bigint), active (bool), created\_at, metadata (jsonb)  
* station\_statistics  
  * id (uuid, PK), station\_id (uuid, FK geo.locations), category (text), period (text), incident\_count (int), created\_at  
* missing\_people  
  * id (uuid, PK), saps\_id, name, case\_ref, station, date\_missing (date), details, region, category (text, default missing\_person), source\_url (unique), embedding\_id (uuid), created\_at  
* wanted\_people  
  * id (uuid, PK), saps\_id, name, case\_ref, crime\_type, crime\_circumstances, station, region, gender, aliases (text\[\]), investigating\_officer, contact\_details, source\_url (unique), embedding\_id (uuid), created\_at  
* unknown\_people  
  * id (uuid, PK), saps\_uid (unique), province, gender, race, estimated\_age, discovery\_date (date), station, details, source\_url (unique), image\_url, created\_at, updated\_at  
* structured\_crime\_intelligence  
  * id (uuid, PK), incident\_type, location, severity, source, incident\_date (date), data (jsonb), created\_at (timestamptz)  
* crime\_reports  
  * id (uuid, PK), incident\_id, date (date), category\_of\_crime, location\_province\_area, region, perpetrators\_details, victims\_details, weapons\_drugs\_contraband\_seized, modus\_operandi, vehicle\_details, other\_intelligence\_data, embedding\_id (uuid), created\_at, location\_id (uuid, FK geo.locations), incident\_type, description, occurred\_at (timestamptz), metadata (jsonb)  
* syndicates  
  * id (uuid, PK), name, type, primary\_territory, estimated\_members (int), risk\_score (int), metadata (jsonb), created\_at, operational\_territory\_geom (geometry)

---

## markets

* ref\_tickers  
  * ticker\_symbol (text, PK), company\_name, sector, industry, asset\_type, is\_active (bool)  
* ref\_countries  
  * country\_code (text, PK), country\_name (text, unique), currency\_code  
* macro\_indicators  
  * date (date, PK part), country\_code (text, PK part, FK ref\_countries), fx\_rate\_usd (numeric), policy\_rate\_pct (numeric), bond\_yield\_10y (numeric), yield\_spread\_us (numeric), equity\_index\_level (numeric), oil\_price\_usd (numeric), updated\_at  
* global\_markets  
  * date (text), ticker (text), company\_name, open (float8), close (float8), volume (text), region, exchange, currency  
* daily\_metrics  
  * date (text), ticker\_symbol (text), price\_open (float8), price\_current (float8), day\_change\_percent (float8), volume (text)  
* int\_news  
  * title, url, published (timestamptz), summary, sentiment, source, market\_impact\_score, mentioned  
* risk\_signals  
  * date (text), vix\_close (float8), sentiment\_score (float8), geopolitical\_risk\_score (float8), currency\_index (float8), economic\_news\_flag (text)

---

## sports\_intelligence

* athletes  
  * id (uuid, PK), full\_name, nickname, birth\_date, height\_cm (numeric), weight\_kg (numeric), reach\_cm (numeric), stance, team\_association, external\_ids (jsonb), updated\_at, nationality, team, hometown, bio\_summary, wiki\_url, org\_id (uuid), wins (int), losses (int), draws (int), no\_contests (int), sport\_name, gender, status, person\_id (uuid, FK people.master\_identities), age (int), bmi (numeric), weight\_class\_normalized, country\_code, profile\_confidence (numeric), created\_at  
* events  
  * id (uuid, PK), org\_id (uuid), event\_name, brand, date\_utc (timestamptz), location, venue, is\_completed (bool), source\_url (unique), event\_number (int), is\_enriched (bool), attendance (int), event\_date (date), sport\_name, venue\_name, created\_at  
* bouts  
  * id (uuid, PK), event\_id (uuid), fighter\_a\_id (uuid), fighter\_b\_id (uuid), weight\_class, is\_title\_fight (bool), winner\_id (uuid), method, method\_detail, round\_end (int), time\_end, stats\_json (jsonb), betting\_odds\_avg (numeric), fight\_duration\_seconds (int), fighter\_a\_kd (int), fighter\_a\_str (int), fighter\_a\_td (int), fighter\_a\_sub (int), fighter\_b\_kd (int), fighter\_b\_str (int), fighter\_b\_td (int), fighter\_b\_sub (int), title\_name, referee\_name, win\_method\_specific, performance\_bonus (bool), is\_interim\_title (bool)  
* news  
  * id (uuid, PK), title, url (unique), source\_domain, published\_at (timestamp), related\_fighter\_id (uuid), sentiment\_score (numeric), category, structured\_data (jsonb), summary  
* ranking\_history  
  * id (uuid, PK), athlete\_id (uuid), organization\_id (uuid), weight\_class, rank (int), date\_captured (date)  
* fight\_stats  
  * id (uuid, PK), bout\_id (uuid), fighter\_id (uuid), knockdowns (int), total\_strikes\_attempted (int), total\_strikes\_landed (int), takedowns\_attempted (int), takedowns\_landed (int), submission\_attempts (int), control\_time\_seconds (int), sponsors (text\[\])  
* round\_stats  
  * id (uuid, PK), bout\_id (uuid), round\_num (int), fighter\_id (uuid), kd (int), sig\_str\_landed (int), sig\_str\_attempted (int), total\_str\_landed (int), total\_str\_attempted (int), td\_landed (int), td\_attempted (int), sub\_att (int), rev (int), ctrl\_seconds (int), created\_at, head\_str\_att (int), head\_str\_landed (int), body\_str\_att (int), body\_str\_landed (int), leg\_str\_att (int), leg\_str\_landed (int), dist\_str\_att (int), dist\_str\_landed (int), clinch\_str\_att (int), clinch\_str\_landed (int), gnd\_str\_att (int), gnd\_str\_landed (int), guard\_passes (int), reversals (int)  
* title\_reigns  
  * id (uuid, PK), fighter\_id (uuid), weight\_class, date\_won (date), date\_lost (date), defenses (int), is\_interim (bool), promotion, created\_at  
* teams  
  * id (uuid, PK), name, short\_name, sport, league\_name, home\_venue\_id (uuid), metadata (jsonb), created\_at  
* judges\_scores  
  * id (uuid, PK), bout\_id (uuid), judge\_name, fighter\_a\_score (int), fighter\_b\_score (int), scorecard\_json (jsonb), created\_at  
* fighter\_status  
  * id (uuid, PK), athlete\_id (uuid), status\_type, details, severity\_score (int), source\_url, is\_active (bool), created\_at  
* fight\_predictions  
  * id (uuid, PK), event\_id (uuid), bout\_id (uuid, unique), predicted\_winner\_id (uuid), confidence\_score (int), method\_prediction, ai\_analysis\_summary, key\_factors (jsonb), created\_at, updated\_at

---

## ai\_intelligence

* trends  
  * id (uuid, PK), cluster\_topic (text), sector (text), region (text), trend\_score (integer), velocity (double precision), data\_volume (integer), related\_entities (text\[\]), sentiment\_id (uuid), summary (text), published\_at (timestamp), created\_at (timestamp), cluster\_id (text), llm\_momentum\_score (double precision), internal\_trend\_score (double precision), sentiment\_score (double precision), score\_components (jsonb), mentioned\_locations (text\[\]), mentioned\_people (text\[\]), mentioned\_organizations (text\[\]), mentioned\_products (text\[\]), mentioned\_events (text\[\]), mentioned\_technologies (text\[\]), mentioned\_financial\_instruments (text\[\]), mentioned\_scientific\_concepts (text\[\]), mentioned\_regulations\_and\_policies (text\[\]), mentioned\_economic\_indicators (text\[\]), articles\_count (integer), articles (jsonb), data (jsonb), domain\_id (uuid), sentiment\_label (text), metadata (jsonb), dedup\_hash (text), ingestion\_ts (timestamptz), canonical\_url (text)  
* sentiment  
  * id (uuid, PK), trend\_id (uuid), positivity (double precision), negativity (double precision), neutrality (double precision), volatility (double precision), dominant\_emotion (text), emotion\_profile (jsonb), ai\_summary (text), created\_at (timestamp)  
* insights  
  * id (uuid, PK), trend\_id (uuid), topic (text), recommended\_platform (text), ai\_summary (text), best\_strategy (text), script\_template (jsonb), caption\_ideas (text\[\]), keywords (text\[\]), generated\_at (timestamp)  
* domains  
  * id (uuid, PK), domain\_name (text, unique), subdomain (text), description (text), created\_at (timestamp)  
* entries  
  * id (uuid, PK), domain\_id (uuid), source (text), title (text), summary (text), content (text), category (text), region (text), sentiment\_score (double precision), sentiment\_label (text), tags (text\[\]), data (jsonb), published\_date (timestamp), created\_at (timestamp), dedup\_hash (text), ingestion\_ts (timestamptz), canonical\_url (text)  
* content\_assets  
  * id (uuid, PK), domain\_id (uuid), trend\_id (uuid), topic (text), content\_type (text), tone (text), platform (text), language (text), ai\_script (text), ai\_caption (text), metadata (jsonb), created\_at (timestamp)  
* real\_estate  
  * id (bigint, identity, PK), created\_at (timestamptz), title (text), url (text, unique), source\_feed (text), published (text), market\_dynamic (text), category (text), ai\_summary (text), locations (text\[\]), companies (text\[\]), statistics (text\[\]), method (text), raw\_context\_source (text), snippet\_sources (jsonb)  
* gaming  
  * id (bigint, identity, PK), created\_at (timestamptz), title (text), url (text, unique), source\_feed (text), published (text), sentiment (text), category (text), ai\_summary (text), key\_entities (text\[\]), method (text), raw\_context\_source (text), snippet\_sources (jsonb)  
* foodtech  
  * id (bigint, identity, PK), created\_at (timestamptz), title (text), url (text, unique), published (text), category (text), impact\_score (integer), companies (text\[\]), technologies (text\[\]), commodities (text\[\]), ai\_summary (text), raw\_context\_source (text), method (text), source\_feed (text), content\_type (text), data\_source\_method (text), markdown\_content (text), key\_entities (text\[\]), sentiment (text), source (text), summary (text), snippet\_sources (jsonb)  
* web3  
  * id (bigint, identity, PK), created\_at (timestamptz), title (text), url (text, unique), published (text), category (text), sentiment (integer), trading\_signal (text), key\_entities (text\[\]), smart\_contracts (text\[\]), ai\_summary (text), method (text), source\_feed (text), raw\_context\_source (text), risk\_level (text), snippet\_sources (jsonb)  
* venture\_capital  
  * id (bigint, identity, PK), created\_at (timestamptz), title (text), url (text, unique), source (text), published (text), category (text), deal\_size (text), round\_stage (text), investors (text\[\]), valuation (text), sentiment (text), industry\_vertical (text), ai\_summary (text), markdown\_content (text), raw\_context\_source (text), method (text), source\_feed (text), content\_type (text), data\_source\_method (text), companies\_mentioned (text\[\]), key\_entities (text\[\]), summary (text), snippet\_sources (jsonb)  
* cybersecurity  
  * id (bigint, identity, PK), created\_at (timestamptz), title (text), url (text, unique), source\_feed (text), risk\_level (text), category (text), ai\_summary (text), key\_entities (text\[\]), raw\_context\_source (text), method (text), snippet\_sources (jsonb)  
* global\_markets  
  * id (bigint, identity, PK not defined in catalog; treated as feed-like): Not present here; note this exists in markets schema, not ai\_intelligence. In ai\_intelligence there is:  
  * global\_markets (separate to markets.global\_markets): title (text), url (text, unique), published (text/timestamp depends on table; see below). Correction: In ai\_intelligence, there is table global\_markets with columns: id not present; actual ai\_intelligence “global\_markets” is not listed — please ignore.  
* health\_fitness  
  * id (bigint, identity, PK), created\_at (timestamptz), title (text), url (text, unique), source (text), published (text), impact\_score (integer), sentiment (text), key\_ingredients (text\[\]), mentioned\_products (text\[\]), target\_body\_parts (text\[\]), category (text), ai\_summary (text), raw\_context\_source (text), method (text), source\_feed (text), content\_type (text), data\_source\_method (text), markdown\_content (text), key\_entities (text\[\]), summary (text), snippet\_sources (jsonb)  
* on\_this\_day  
  * day\_id (text, PK), date\_display (text), events (jsonb), births (jsonb), deaths (jsonb), holidays (jsonb), source\_urls (jsonb), last\_updated (timestamptz), created\_at (timestamptz), holidays\_major (text\[\]), observances\_intl (text\[\]), observances\_fun (text\[\]), zodiac\_sign (text), birthstone (text), birth\_flower (text), news\_milestones (jsonb), social\_content (jsonb), niche\_data (jsonb)  
* on\_this\_day\_events  
  * id (uuid, PK), day\_id (text, FK on\_this\_day), year (integer), title (text), summary (text), entities\_json (jsonb), locations\_json (jsonb), occurred\_on (date), source\_url (text), created\_at (timestamptz)  
* event\_entity\_links  
  * id (uuid, PK), event\_id (uuid, FK on\_this\_day\_events), entity\_type (text), raw\_value (text), canonical\_entity\_id (uuid), method (text), confidence (numeric), is\_locked (bool), reviewed\_by (uuid), reviewed\_at (timestamptz), created\_at (timestamptz)  
* event\_temporal\_links  
  * id (uuid, PK), event\_id (uuid, FK on\_this\_day\_events), temporal\_role (text), date\_value (date), tsrange\_value (tsrange), confidence (numeric), created\_at (timestamptz)  
* entity\_links  
  * id (uuid, PK), source\_schema (text), source\_table (text), source\_id (uuid), entity\_type (text), raw\_value (text), target\_entity\_id (uuid), method (text), confidence (numeric), is\_locked (bool), reviewed\_by (uuid), reviewed\_at (timestamptz), created\_at (timestamptz)  
* weather\_cache  
  * ward\_code (text, PK), latitude (numeric), longitude (numeric), temperature\_c (numeric), condition\_text (text), condition\_icon (text), wind\_kph (numeric), humidity (integer), is\_day (boolean), fetched\_at (timestamptz), raw\_response (jsonb), created\_at (timestamptz), updated\_at (timestamptz), precip\_mm (numeric), daily\_forecast (jsonb), alerts\_summary (jsonb)  
* alerts  
  * id (uuid, PK), category (text), severity (text), scope\_level (text), scope\_code (text), title (text), summary (text), intelligence\_sources (jsonb), confidence\_score (numeric), created\_at (timestamptz), expires\_at (timestamptz), subcategory (text), source (text), source\_ref (text), is\_active (boolean), dismissed\_count (integer)  
* weather\_alerts  
  * id (uuid, PK), ward\_code (varchar, FK weather\_cache), event (varchar), headline (text), description (text), severity (varchar), urgency (varchar), areas (text), category (varchar), certainty (varchar), instruction (text), effective (timestamptz), expires (timestamptz), created\_at (timestamptz), updated\_at (timestamptz)  
* ai\_knowledge\_base  
  * id (uuid, PK), content (text), metadata (jsonb), embedding (vector), created\_at (timestamptz), updated\_at (timestamptz), source (text), source\_type (text), ward\_code (text)  
* analytics\_events  
  * id (uuid, PK), event\_type (text), path (text), ward\_code (text), visitor\_hash (text), session\_id (text), device\_type (text), referrer (text), country (text), metadata (jsonb), created\_at (timestamptz)  
* news\_articles  
  * id (uuid, PK), title (text), slug (text, unique), summary (text), content (text), category (text), scope (text), ward\_codes (text\[\]), municipality\_codes (text\[\]), province\_codes (text\[\]), source\_url (text, unique), source\_name (text), author\_name (text), image\_url (text), published\_at (timestamptz), topics (text\[\]), ai\_summary (text), sentiment (text), priority (int), is\_featured (bool), is\_published (bool), created\_at (timestamptz), updated\_at (timestamptz)  
* historical\_records  
  * id (uuid, PK), title (text), summary (text), content (text), event\_date (text), day\_id (text, FK on\_this\_day), publisher (text), language (text), category (text), source\_url (text, unique), pdf\_url (text), thumbnail\_url (text), entities (jsonb), tags (text\[\]), ai\_analysis (jsonb), created\_at (timestamp), updated\_at (timestamp), location\_text (text), location\_point (geometry), ward\_code (text), signal\_category (text)  
* feed\_items  
  * id (uuid, PK), domain\_id (uuid, FK domains), title (text), url (text), published\_at (timestamptz), summary (text), content (text), sentiment\_score (double precision), sentiment\_label (text), risk\_level (text), entities\_mentioned (text\[\]), metadata (jsonb), created\_at (timestamptz), dedup\_hash (text, unique), origin\_feed (text)


