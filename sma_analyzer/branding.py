"""Offline company/ETF issuer identities. No logo requests or ticker API calls."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ETFIssuer:
    key: str
    name: str
    aliases: tuple[str,...]
    source_ticker: str


# A maintained coverage catalogue, not a live assets-under-management ranking.
ETF_ISSUERS=(
    ETFIssuer("vanguard","Vanguard",("vanguard",),"VOO"),
    ETFIssuer("blackrock","BlackRock / iShares",("ishares","blackrock"),"BLK"),
    ETFIssuer("state-street","State Street",("state street","spdr","ssga"),"SPY"),
    ETFIssuer("invesco","Invesco",("invesco","powershares"),"QQQ"),
    ETFIssuer("schwab","Charles Schwab",("schwab","charles schwab"),"SCHB"),
    ETFIssuer("jpmorgan","J.P. Morgan",("jpmorgan","jp morgan","j p morgan"),"JEPI"),
    ETFIssuer("dimensional","Dimensional Fund Advisors",("dimensional","dfa"),"DFAC"),
    ETFIssuer("first-trust","First Trust",("first trust","ft vest","ft cboe vest"),"FTCS"),
    ETFIssuer("vaneck","VanEck",("vaneck","van eck"),"SMH"),
    ETFIssuer("proshares","ProShares",("proshares",),"TQQQ"),
    ETFIssuer("wisdomtree","WisdomTree",("wisdomtree","wisdom tree"),"USFR"),
    ETFIssuer("fidelity","Fidelity Investments",("fidelity",),""),
    ETFIssuer("capital-group","Capital Group",("capital group",),"CGUS"),
    ETFIssuer("goldman-sachs","Goldman Sachs",("goldman sachs","goldman"),"GS"),
    ETFIssuer("global-x","Global X",("global x","globalx"),"QYLD"),
    ETFIssuer("american-century","American Century Investments",("american century","avantis"),"FLV"),
    ETFIssuer("franklin-templeton","Franklin Templeton",("franklin","templeton","legg mason","clearbridge"),"BEN"),
    ETFIssuer("pimco","PIMCO",("pimco",),"BOND"),
    ETFIssuer("pacer","Pacer",("pacer",),"COWZ"),
    ETFIssuer("janus-henderson","Janus Henderson",("janus henderson","janus"),"JAAA"),
    ETFIssuer("innovator","Innovator",("innovator",),"PJAN"),
    ETFIssuer("direxion","Direxion",("direxion",),"SPXL"),
    ETFIssuer("pgim","PGIM / Prudential",("pgim","prudential"),"PULS"),
    ETFIssuer("t-rowe-price","T. Rowe Price",("t rowe price",),"TROW"),
    ETFIssuer("ark","ARK Investment Management",("ark","21shares ark"),"ARKK"),
    ETFIssuer("harbor","Harbor Capital",("harbor",),"HGER"),
    ETFIssuer("roundhill","Roundhill Investments",("roundhill",),"MAGS"),
    ETFIssuer("alpha-architect","Alpha Architect",("alpha architect",),"BOXX"),
    ETFIssuer("amplify","Amplify ETFs",("amplify",),"DIVO"),
    ETFIssuer("alps","ALPS / SS&C",("alps","ss c alps"),"SDOG"),
)

_BY_KEY={issuer.key:issuer for issuer in ETF_ISSUERS}
_ETF_SYMBOLS={}
for _issuer,_symbols in {
    "vanguard":"VOO VTI VXUS VEA VWO BND BNDX VUG VTV VT VIG VYM VGK VNQ VO VB VGT VHT VDC VPU VFH VDE VBR VCSH VGLT",
    "blackrock":"IVV IWM EFA EEM AGG TLT IEF SHY LQD HYG IAU ITOT IXUS QUAL USMV SGOV IBIT IEMG IEFA IJR IJS IJH IVW IVLU ACWI",
    "state-street":"SPY SPLG SPYM SPYG SPYV DIA GLD GLDM XLF XLK XLE XLV XLY XLP XLU XLB XLI XLRE XLC BIL SPTM SPDW SPAB SPDW SPEM SPMD SPTL",
    "invesco":"QQQ QQQM RSP QQQJ SPMO DBB DBC DBE DBP DBA BKLN PGX PDBC",
    "schwab":"SCHB SCHD SCHF SCHG SCHH SCHX SCHA SCHM SCHE SCHZ SCHP SCHO SCHR",
    "jpmorgan":"JEPI JEPQ JPST JPIE JQUA JPME JCPB JMUB BBUS",
    "fidelity":"FBTC FETH FTEC FDVV FBCG ONEQ FIDU FDRR FIDI FENY FSTA FHLC FREL FDIS FCOM FLDR FVAL FMIL FPRO FELG FELC",
    "wisdomtree":"USFR DGRW NTSX NTSI NTSE DXJ DGS",
    "alpha-architect":"BOXX QVAL IVAL QMOM IMOM VMOT HIDE",
    "roundhill":"MAGS BETZ MEME CHAT NERD METV WEED RDTE XDTE QDTE YBTC",
    "global-x":"QYLD XYLD RYLD QYLG XYLG BOTZ LIT DRIV AIQ COPX URA GXG",
    "american-century":"AVUV AVUS AVEM AVDE AVIV AVES AVES AVSC AVMC AVMA AVNM AVGV AVGE FLV FDG KORP VALQ",
    "first-trust":"FTCS FDN FVD FV FPE FMB RDVY SKYY CIBR FTHI",
    "proshares":"TQQQ SQQQ UPRO SPXU PSQ SH QLD QID BITO NOBL",
    "pimco":"BOND MINT HYS CORP STPZ",
    "pacer":"COWZ CALF GCOW ECOW ICOW HERD",
    "direxion":"SPXL SPXS SOXL SOXS TNA TZA LABU LABD FAS FAZ NAIL TECL TECS",
    "capital-group":"CGUS CGGR CGDV CGXU CGGO CGCP CGMS CGSD CGMU",
    "pgim":"PULS",
    "janus-henderson":"JAAA JBBB JSI VNLA JIII JAND",
    "innovator":"PJAN PJUL UJAN BJAN EJAN DJAN KJAN",
    "harbor":"HGER HAPY HARP SIHY SIFI",
    "amplify":"DIVO BATT IBUY BLOK YYY CNBS",
    "alps":"SDOG ACES AMLP",
}.items():
    for _symbol in _symbols.split():
        _ETF_SYMBOLS[_symbol]=_issuer

# Equity identities and old cached SGX symbols share the same packaged logos.
STOCK_LOGOS={"AAPL":"apple","MSFT":"microsoft","GOOG":"google","GOOGL":"google",
             "TSLA":"tesla","NVDA":"nvidia","NFLX":"netflix","C6L":"singaporeairlines",
             "D05":"dbs","DBSDF":"dbs","DBSDY":"dbs","BLK":"blackrock","STT":"state-street",
             "IVZ":"invesco","SCHW":"schwab","JPM":"jpmorgan","GS":"goldman-sachs",
             "BEN":"franklin-templeton","TROW":"t-rowe-price","WT":"wisdomtree"}


def _words(value):
    return " ".join(re.findall(r"[a-z0-9]+",value.casefold()))


def etf_issuer(symbol,name="",family=""):
    key=_ETF_SYMBOLS.get(symbol.upper())
    if key:
        return _BY_KEY[key]
    for value in (family,name):
        text=_words(value)
        for issuer in ETF_ISSUERS:
            if any(text==alias or text.startswith(alias+" ") for alias in issuer.aliases):
                return issuer
    return None


def local_logo(symbol,name="",instrument_type="",issuer=""):
    symbol=symbol.upper().removesuffix(".SI")
    if instrument_type=="EQUITY":
        return STOCK_LOGOS.get(symbol,"")
    if instrument_type!="ETF" and symbol in STOCK_LOGOS:
        return STOCK_LOGOS[symbol]
    known=_BY_KEY.get(issuer) or etf_issuer(symbol,name)
    if known and (instrument_type=="ETF" or symbol in _ETF_SYMBOLS or
                  any(word in name.casefold() for word in (" etf"," fund"," trust"))):
        return known.key
    return ""
