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
    if (u.hostname === "data-api.ecb.europa.eu") return text(ECB_CSV, "text/csv");
    if (u.hostname === "sdmx.oecd.org") return text(OECD_CSV, "text/csv");
    if (u.hostname === "ourworldindata.org") return text(OWID_CSV, "text/csv");
    if (u.hostname === "evds2.tcmb.gov.tr") return (init?.headers?.key ?? init?.headers?.get?.("key")) ? json(EVDS_JSON) : new Response("Unauthorized", { status: 401 });
    return new Response("mock: unknown host " + u.hostname, { status: 502 });
  };
  return { calls, restore: () => { globalThis.fetch = real; } };
}
