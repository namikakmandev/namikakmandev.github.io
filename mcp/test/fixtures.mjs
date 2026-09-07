// Canned replies in the shape each provider actually returns, so the parsers can be
// tested where the live hosts are unreachable. Installs a fetch mock that answers
// for those hosts and passes everything else (the local data server) through.

const FRED_CSV = `observation_date,CPIAUCSL
2019-11-01,257.208
2019-12-01,257.971
2020-01-01,258.687
2020-02-01,258.822
2020-03-01,258.246
2020-04-01,256.192
2020-05-01,255.936
2020-06-01,257.104
2020-07-01,258.510
2020-08-01,259.366
2020-09-01,260.149
2020-10-01,260.462
2020-11-01,260.927
2020-12-01,261.560
2021-01-01,262.200
2021-02-01,263.161
2021-03-01,264.793
2021-04-01,266.832
2021-05-01,268.551
2021-06-01,270.981
2021-07-01,272.184
2021-08-01,272.951
2021-09-01,274.138
2021-10-01,276.590
2021-11-01,278.524
2021-12-01,280.126
2022-01-01,.
`;

// JSON-stat 2.0 with two geos and three months; sparse value object as Eurostat sends it.
const EUROSTAT_JSONSTAT = {
  version: "2.0", class: "dataset", label: "HICP - monthly data (index)",
  id: ["freq", "unit", "coicop", "geo", "time"],
  size: [1, 1, 1, 2, 3],
  dimension: {
    freq: { label: "Time frequency", category: { index: { M: 0 }, label: { M: "Monthly" } } },
    unit: { label: "Unit of measure", category: { index: { I15: 0 }, label: { I15: "Index, 2015=100" } } },
    coicop: { label: "Classification", category: { index: { CP00: 0 }, label: { CP00: "All-items HICP" } } },
    geo: { label: "Geopolitical entity", category: { index: { DE: 0, TR: 1 }, label: { DE: "Germany", TR: "Türkiye" } } },
    time: { label: "Time", category: { index: { "2024-01": 0, "2024-02": 1, "2024-03": 2 }, label: { "2024-01": "2024-01", "2024-02": "2024-02", "2024-03": "2024-03" } } },
  },
  value: { "0": 125.1, "1": 125.6, "2": 126.2, "3": 1690.4, "4": 1767.2, "5": 1823.9 },
};

const WORLDBANK = [
  { page: 1, pages: 1, per_page: 20000, total: 4, sourceid: "2", lastupdated: "2026-07-01" },
  [
    { indicator: { id: "NY.GDP.MKTP.CD", value: "GDP (current US$)" }, country: { id: "TR", value: "Turkiye" }, countryiso3code: "TUR", date: "2023", value: 1108022000000, unit: "", obs_status: "", decimal: 0 },
    { indicator: { id: "NY.GDP.MKTP.CD", value: "GDP (current US$)" }, country: { id: "TR", value: "Turkiye" }, countryiso3code: "TUR", date: "2022", value: 907118000000, unit: "", obs_status: "", decimal: 0 },
    { indicator: { id: "NY.GDP.MKTP.CD", value: "GDP (current US$)" }, country: { id: "US", value: "United States" }, countryiso3code: "USA", date: "2023", value: 27360935000000, unit: "", obs_status: "", decimal: 0 },
    { indicator: { id: "NY.GDP.MKTP.CD", value: "GDP (current US$)" }, country: { id: "US", value: "United States" }, countryiso3code: "USA", date: "2022", value: null, unit: "", obs_status: "", decimal: 0 },
  ],
];

const ECB_CSV = `KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE,OBS_STATUS,OBS_CONF,OBS_PRE_BREAK,OBS_COM,TIME_FORMAT,BREAKS,COLLECTION,COMPILING_ORG,DISS_ORG,DOM_SER_IDS,PUBL_ECB,PUBL_MU,PUBL_PUBLIC,UNIT_INDEX_BASE,COMPILATION,COVERAGE,DECIMALS,NAT_TITLE,SOURCE_AGENCY,SOURCE_PUB,TITLE,TITLE_COMPL,UNIT,UNIT_MULT
EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2024-01,1.0905,A,F,,,P1M,,A,,,,,,,,,,4,,4F0,,US dollar/Euro,"ECB reference exchange rate, US dollar/Euro, 2:15 pm (C.E.T.)",USD,0
EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2024-02,1.0795,A,F,,,P1M,,A,,,,,,,,,,4,,4F0,,US dollar/Euro,"ECB reference exchange rate, US dollar/Euro, 2:15 pm (C.E.T.)",USD,0
EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2024-03,1.0872,A,F,,,P1M,,A,,,,,,,,,,4,,4F0,,US dollar/Euro,"ECB reference exchange rate, US dollar/Euro, 2:15 pm (C.E.T.)",USD,0
`;

const OECD_CSV = `STRUCTURE,STRUCTURE_ID,ACTION,REF_AREA,Reference area,FREQ,Frequency of observation,MEASURE,Measure,UNIT_MEASURE,Unit of measure,ACTIVITY,Economic activity,ADJUSTMENT,Adjustment,TRANSFORMATION,Transformation,TIME_PERIOD,Time period,OBS_VALUE,Observation value,OBS_STATUS,Observation status,UNIT_MULT,Unit multiplier,DECIMALS,Decimals
DATAFLOW,OECD.SDD.STES:DSD_STES@DF_CLI(4.1),I,TUR,Türkiye,M,Monthly,LI,Composite leading indicator,IX,Index,_Z,Not applicable,AA,Amplitude adjusted,_Z,Not applicable,2024-01,2024-01,100.4,100.4,A,Normal value,0,Units,2,Two
DATAFLOW,OECD.SDD.STES:DSD_STES@DF_CLI(4.1),I,TUR,Türkiye,M,Monthly,LI,Composite leading indicator,IX,Index,_Z,Not applicable,AA,Amplitude adjusted,_Z,Not applicable,2024-02,2024-02,100.6,100.6,A,Normal value,0,Units,2,Two
DATAFLOW,OECD.SDD.STES:DSD_STES@DF_CLI(4.1),I,USA,United States,M,Monthly,LI,Composite leading indicator,IX,Index,_Z,Not applicable,AA,Amplitude adjusted,_Z,Not applicable,2024-01,2024-01,99.8,99.8,A,Normal value,0,Units,2,Two
DATAFLOW,OECD.SDD.STES:DSD_STES@DF_CLI(4.1),I,USA,United States,M,Monthly,LI,Composite leading indicator,IX,Index,_Z,Not applicable,AA,Amplitude adjusted,_Z,Not applicable,2024-02,2024-02,99.9,99.9,A,Normal value,0,Units,2,Two
`;

const OWID_CSV = `Entity,Code,Year,cattle
Turkey,TUR,2021,18036117
Turkey,TUR,2022,17024129
United States,USA,2021,93790000
United States,USA,2022,91902000
World,OWID_WRL,2022,1547423486
`;

const EVDS_JSON = {
  totalCount: 3,
  items: [
    { Tarih: "2024-1", TP_DK_USD_A: "30.1153", UNIXTIME: { $numberLong: "1704067200" } },
    { Tarih: "2024-2", TP_DK_USD_A: "30.8975", UNIXTIME: { $numberLong: "1706745600" } },
    { Tarih: "2024-3", TP_DK_USD_A: "31.9856", UNIXTIME: { $numberLong: "1709251200" } },
  ],
};

const FRED_SEARCH = { seriess: [{ id: "CPIAUCSL", title: "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average", frequency_short: "M", units_short: "Index 1982-1984=100", seasonal_adjustment_short: "SA", observation_start: "1947-01-01", observation_end: "2026-07-01" }] };

const BIS_CSV = `KEY,FREQ,REF_AREA,VALUE,UNIT_MEASURE,TIME_PERIOD,OBS_VALUE,OBS_STATUS
WS_SPP:Q.TR.N.628,Q,TR,N,628,2024-Q1,1315.4,A
WS_SPP:Q.TR.N.628,Q,TR,N,628,2024-Q2,1402.7,A
WS_SPP:Q.TR.N.628,Q,TR,N,628,2024-Q3,1480.1,A
`;

const FAO_JSON = {
  data: [
    { "Domain Code": "QCL", Domain: "Crops and livestock products", "Area Code": "223", Area: "Türkiye", "Element Code": "5111", Element: "Stocks", "Item Code": "866", Item: "Cattle", "Year Code": "2021", Year: "2021", Unit: "An", Value: "18036117" },
    { "Domain Code": "QCL", Domain: "Crops and livestock products", "Area Code": "223", Area: "Türkiye", "Element Code": "5111", Element: "Stocks", "Item Code": "866", Item: "Cattle", "Year Code": "2022", Year: "2022", Unit: "An", Value: "17024129" },
    { "Domain Code": "QCL", Domain: "Crops and livestock products", "Area Code": "231", Area: "United States of America", "Element Code": "5111", Element: "Stocks", "Item Code": "866", Item: "Cattle", "Year Code": "2021", Year: "2021", Unit: "An", Value: "93790000" },
    { "Domain Code": "QCL", Domain: "Crops and livestock products", "Area Code": "231", Area: "United States of America", "Element Code": "5111", Element: "Stocks", "Item Code": "866", Item: "Cattle", "Year Code": "2022", Year: "2022", Unit: "An", Value: "91902000" },
  ],
};
const FAO_DEFS = { data: [{ code: "866", label: "Cattle" }, { code: "867", label: "Meat of cattle with the bone, fresh or chilled" }, { code: "15", label: "Wheat" }] };

const IMF_CSV = `STRUCTURE,STRUCTURE_ID,ACTION,COUNTRY,INDICATOR,FREQUENCY,TIME_PERIOD,OBS_VALUE,SCALE,UNIT,LASTACTUALDATE,PUBLICATION_DATE
dataflow,IMF.RES:WEO(6.0.0),I,TUR,NGDP_RPCH,A,2023,5.1,Units,Percent,2024,2025-04-22
dataflow,IMF.RES:WEO(6.0.0),I,TUR,NGDP_RPCH,A,2024,3.2,Units,Percent,2024,2025-04-22
dataflow,IMF.RES:WEO(6.0.0),I,TUR,NGDP_RPCH,A,2025,2.7,Units,Percent,2024,2025-04-22
dataflow,IMF.RES:WEO(6.0.0),I,USA,NGDP_RPCH,A,2023,2.9,Units,Percent,2024,2025-04-22
dataflow,IMF.RES:WEO(6.0.0),I,USA,NGDP_RPCH,A,2024,2.8,Units,Percent,2024,2025-04-22
`;
const IMF_FLOWS = { data: { dataflows: [{ id: "WEO", agencyID: "IMF.RES", version: "6.0.0", name: "World Economic Outlook (WEO)" }, { id: "CPI", agencyID: "IMF.STA", version: "4.0.0", name: "Consumer Price Index (CPI)" }] } };

// Open-Meteo archive: two locations, three days, the array form the API returns for multi-point requests.
const OPENMETEO = [
  { latitude: 41.6, longitude: -93.6, daily_units: { time: "iso8601", temperature_2m_mean: "°C", precipitation_sum: "mm" },
    daily: { time: ["2024-06-29", "2024-06-30", "2024-07-01"], temperature_2m_mean: [22.5, 23.5, 25.0], precipitation_sum: [4.0, 6.0, 1.5] } },
  { latitude: 37.87, longitude: 32.49, daily_units: { time: "iso8601", temperature_2m_mean: "°C", precipitation_sum: "mm" },
    daily: { time: ["2024-06-29", "2024-06-30", "2024-07-01"], temperature_2m_mean: [20.0, 22.0, 24.0], precipitation_sum: [0.0, null, 2.5] } },
];

// SEC EDGAR: the ticker directory, then company facts for one tag at a time.
// Shape as data.sec.gov sends it: overlapping facts, restatements, a `frame` on the
// rows the SEC itself has aligned to a calendar period.
let secBlocked = false;
export function setSecBlocked(v) { secBlocked = v; }
const SEC_TICKERS = {
  "0": { cik_str: 320193, ticker: "AAPL", title: "Apple Inc." },
  "1": { cik_str: 789019, ticker: "MSFT", title: "MICROSOFT CORP" },
  "2": { cik_str: 51143, ticker: "IBM", title: "INTERNATIONAL BUSINESS MACHINES CORP" },
};
const SEC_ASSETS = {
  cik: 320193, taxonomy: "us-gaap", tag: "Assets", label: "Assets", entityName: "Apple Inc.",
  units: { USD: [
    { end: "2023-04-01", val: 332160000000, accn: "a1", fy: 2023, fp: "Q2", form: "10-Q", filed: "2023-05-05", frame: "CY2023Q1I" },
    { end: "2023-07-01", val: 335038000000, accn: "a2", fy: 2023, fp: "Q3", form: "10-Q", filed: "2023-08-04", frame: "CY2023Q2I" },
    { end: "2023-09-30", val: 352583000000, accn: "a3", fy: 2023, fp: "FY", form: "10-K", filed: "2023-11-03", frame: "CY2023Q3I" },
    { end: "2023-09-30", val: 352000000000, accn: "a3-old", fy: 2023, fp: "FY", form: "10-K", filed: "2023-11-01" },
    { end: "2023-12-30", val: 353514000000, accn: "a4", fy: 2024, fp: "Q1", form: "10-Q", filed: "2024-02-02", frame: "CY2023Q4I" },
  ] },
};
const SEC_EQUITY = {
  cik: 320193, taxonomy: "us-gaap", tag: "StockholdersEquity", label: "Stockholders' Equity", entityName: "Apple Inc.",
  units: { USD: [
    { end: "2023-04-01", val: 62158000000, form: "10-Q", filed: "2023-05-05", frame: "CY2023Q1I" },
    { end: "2023-07-01", val: 60274000000, form: "10-Q", filed: "2023-08-04", frame: "CY2023Q2I" },
    { end: "2023-09-30", val: 62146000000, form: "10-K", filed: "2023-11-03", frame: "CY2023Q3I" },
  ] },
};
const SEC_NETINCOME = {
  cik: 320193, taxonomy: "us-gaap", tag: "NetIncomeLoss", label: "Net Income (Loss)", entityName: "Apple Inc.",
  units: { USD: [
    { start: "2023-01-01", end: "2023-04-01", val: 24160000000, form: "10-Q", filed: "2023-05-05", frame: "CY2023Q1" },
    { start: "2023-04-02", end: "2023-07-01", val: 19881000000, form: "10-Q", filed: "2023-08-04", frame: "CY2023Q2" },
    { start: "2022-10-02", end: "2023-09-30", val: 96995000000, form: "10-K", filed: "2023-11-03", frame: "CY2023" },
    { start: "2023-07-02", end: "2023-09-30", val: 22956000000, form: "10-K", filed: "2023-11-03", frame: "CY2023Q3" },
  ] },
};

export function installFetchMock() {
  const real = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const u = new URL(url);
    calls.push(url);
    const text = (body, type = "text/plain") => new Response(body, { status: 200, headers: { "content-type": type } });
    const json = (body) => text(JSON.stringify(body), "application/json");
    if (u.hostname === "127.0.0.1" || u.hostname === "localhost") return real(input, init);
    if (u.hostname === "fred.stlouisfed.org") return u.searchParams.get("id") === "CPIAUCSL" ? text(FRED_CSV, "text/csv") : text("", "text/csv");
    if (u.hostname === "api.stlouisfed.org") return json(FRED_SEARCH);
    if (u.hostname === "ec.europa.eu") return u.pathname.includes("prc_hicp_midx") ? json(EUROSTAT_JSONSTAT) : json({ error: { status: 404, label: "Dataset not found" } });
    if (u.hostname === "api.worldbank.org") return u.pathname.includes("/indicator?") || u.pathname.endsWith("/indicator") ? json([{ pages: 1 }, [{ id: "NY.GDP.MKTP.CD", name: "GDP (current US$)", sourceNote: "GDP at purchaser's prices" }]]) : json(WORLDBANK);
    if (u.hostname === "archive-api.open-meteo.com") {
      // The real API returns a bare object for one location and an array for several.
      const n = (u.searchParams.get("latitude") || "").split(",").length;
      return json(n === 1 ? OPENMETEO[0] : OPENMETEO.slice(0, n));
    }
    // The SEC refuses callers it does not like; the provider must say so rather than
    // reporting every company as unknown.
    if (u.hostname === "www.sec.gov") return secBlocked ? new Response("<!DOCTYPE html><html><head><title>SEC.gov | Request Rate Threshold Exceeded</title></head><body><h1>Your Request Originates from an Undeclared Automated Tool</h1><p>Please declare your traffic by updating your user agent.</p></body></html>", { status: 403 }) : json(SEC_TICKERS);
    if (u.hostname === "data.sec.gov") {
      if (u.pathname.endsWith("/Assets.json")) return json(SEC_ASSETS);
      if (u.pathname.endsWith("/NetIncomeLoss.json")) return json(SEC_NETINCOME);
      if (u.pathname.endsWith("/StockholdersEquity.json")) return json(SEC_EQUITY);
      return new Response(JSON.stringify({ error: "not found" }), { status: 404 });
    }
    if (u.hostname === "data-api.ecb.europa.eu") return text(ECB_CSV, "text/csv");
    if (u.hostname === "sdmx.oecd.org") return text(OECD_CSV, "text/csv");
    if (u.hostname === "ourworldindata.org") return text(OWID_CSV, "text/csv");
    if (u.hostname === "stats.bis.org") return text(BIS_CSV, "text/csv");
    if (u.hostname === "api.imf.org") return u.pathname.includes("/structure/") ? json(IMF_FLOWS) : u.pathname.includes("/WEO/") ? text(IMF_CSV, "text/csv") : text("STRUCTURE,STRUCTURE_ID,ACTION,TIME_PERIOD,OBS_VALUE\n", "text/csv");
    if (u.hostname === "faostatservices.fao.org") {
      if (u.pathname.endsWith("/auth/login")) {
        const body = String(init?.body ?? "");
        return /username=fao%40example\.com&password=pw/.test(body) ? json({ AuthenticationResult: { AccessToken: "jwt-1", RefreshToken: "r" } }) : new Response(JSON.stringify({ message: "bad credentials" }), { status: 401 });
      }
      const auth = init?.headers?.authorization ?? init?.headers?.get?.("authorization") ?? "";
      if (auth !== "Bearer jwt-1") return new Response(JSON.stringify({ message: "Missing Authorization Header" }), { status: 401 });
      return u.pathname.includes("/definitions/") ? json(FAO_DEFS) : json(FAO_JSON);
    }
    if (u.hostname === "evds3.tcmb.gov.tr" && u.pathname.includes("/datagroups/")) return json([{ DATAGROUP_CODE: "bie_fiyattufe", DATAGROUP_NAME_ENG: "Consumer Price Index (2025=100)" }, { DATAGROUP_CODE: "bie_kfe", DATAGROUP_NAME_ENG: "Residential Property Price Index" }]);
    if (u.hostname === "evds3.tcmb.gov.tr" && u.pathname.includes("/serieList/")) return json([{ SERIE_CODE: "TP.FG.J0X", SERIE_NAME_ENG: "CPI general index (2025=100)", FREQUENCY_STR: "MONTHLY", START_DATE: "01-01-2025" }]);
    if (u.hostname === "evds3.tcmb.gov.tr" && u.pathname.startsWith("/igmevdsms-dis/")) return (init?.headers?.key ?? init?.headers?.get?.("key")) ? json(EVDS_JSON) : new Response("Unauthorized", { status: 401 });
    return new Response("mock: unknown host " + u.hostname, { status: 502 });
  };
  return { calls, restore: () => { globalThis.fetch = real; } };
}
