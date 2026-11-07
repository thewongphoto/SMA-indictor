from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from sma_analyzer.branding import ETF_ISSUERS
from sma_analyzer.market_cache import MarketCache
from sma_analyzer.securities import Security,security_by_key
from sma_analyzer.yahoo import security_from_quote


class OfflineLogoTests(TestCase):
    def test_dbs_uses_packaged_logo_in_new_and_preexisting_cached_records(self):
        self.assertTrue(security_by_key("SGX:D05").logo_path.endswith("dbs.png"))
        with TemporaryDirectory() as directory:
            path=Path(directory)/"cache.sqlite3"
            old=Security("YAHOO:D05.SI","D05.SI","DBS Group Holdings Ltd","SGX","DG",provider="yahoo",symbol="D05.SI")
            MarketCache(path).put_security(old)
            with patch("urllib.request.urlopen",side_effect=AssertionError("Logos must be local")):
                cached=MarketCache(path).security(old.key)
                self.assertTrue(cached.logo_path.endswith("dbs.png"))
                self.assertTrue(Path(cached.logo_path).is_file())

    def test_voo_uses_vanguard_spy_uses_state_street_and_etf_type_is_retained(self):
        for symbol,name,expected in (("VOO","Vanguard S&P 500 ETF","vanguard"),
                                     ("SPY","SPDR S&P 500 ETF Trust","state-street"),
                                     ("FTEC","Fidelity MSCI Information Technology Index ETF","fidelity")):
            security=security_from_quote(dict(symbol=symbol,longname=name,exchange="PCX",quoteType="ETF"))
            self.assertEqual((security.instrument_type,security.issuer),("ETF",expected))
            self.assertTrue(security.logo_path.endswith(expected+".png"))

    def test_thirty_provider_images_cover_name_prefixes_without_symbol_whitelisting(self):
        self.assertEqual(len(ETF_ISSUERS),30)
        for issuer in ETF_ISSUERS:
            with self.subTest(issuer=issuer.key):
                # Unknown ticker, recognized sponsor name: no API metadata call.
                security=security_from_quote(dict(symbol="UNLISTEDTEST",longname=issuer.aliases[0]+" Global ETF",
                                                  exchange="PCX",quoteType="ETF"))
                self.assertEqual(security.issuer,issuer.key)
                p=Path(security.logo_path)
                self.assertTrue(p.is_file())
                self.assertTrue(p.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertLess(p.stat().st_size,32768)
        root=Path(__file__).parents[1]/"sma_analyzer"/"assets"/"logos"
        self.assertLess(sum((root/(issuer.key+".png")).stat().st_size for issuer in ETF_ISSUERS),256*1024)

    def test_old_etf_cache_gains_logo_without_history_deletion(self):
        with TemporaryDirectory() as directory:
            cache=MarketCache(Path(directory)/"cache.sqlite3")
            security=Security("YAHOO:VOO","VOO","Vanguard S&P 500 ETF","NYSE Arca","VS",provider="yahoo")
            cache.put_security(security)
            cached=cache.security(security.key)
            self.assertTrue(cached.logo_path.endswith("vanguard.png"))
            self.assertEqual((cached.key,cached.name),(security.key,security.name))

    def test_unknown_funds_fall_back_and_equity_names_do_not_borrow_etf_brand(self):
        unknown=security_from_quote(dict(symbol="UNKNOWNTEST",longname="Independent Global ETF",exchange="PCX",quoteType="ETF"))
        equity=security_from_quote(dict(symbol="FNF",longname="Fidelity National Financial",exchange="NYQ",quoteType="EQUITY"))
        self.assertEqual((unknown.logo_path,equity.logo_path),("",""))
