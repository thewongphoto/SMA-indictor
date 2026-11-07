# Offline company and ETF issuer logos

Added 7 November 2026 for private app testing. The app bundles DBS and 30 major US ETF issuer/brand PNGs; no logo network requests occur at runtime. VOO uses Vanguard and SPY uses State Street.

The coverage list below is explicit and maintained. A current AUM top-30 league table could not be verified because this environment blocks the ETFdb issuer-ranking website. The catalogue is not presented as a current ranking. Unknown providers keep the initials fallback.

## API capability

The supported yfinance Search/Ticker.history interface does not provide a documented, reliable company/ETF-issuer logo API. Historical examples using `info["logo_url"]` are not a supported logo feed. The app uses locally bundled assets rather than adding metadata or third-party logo API calls. See the [API reference](https://ranaroussi.github.io/yfinance/reference/index.html).

## Sources and assets

Brand marks belong to their respective owners and identify the company/issuer; they do not indicate endorsement. Assets were copied as PNGs, without synthesizing replacement logos. Existing Simple Icons credits remain in `sma_analyzer/assets/logos/CREDITS.txt`.

| Provider | Match examples | PNG source | Bytes | SHA-256 |
| --- | --- | --- | ---: | --- |
| ALPS / SS&C | alps, ss c alps | [alps.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/SDOG.png) | 1,704 | `ed13de55c15e2f4c83fd82a84026dbe12aa1464cb256c56a1f1fa508c0dd2a21` |
| ARK Investment Management | ark, 21shares ark | [ark.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/ARKK.png) | 14,331 | `93a06ed238172eac730978b607d6685904113b6051cf24ecea1a19ae6d9bf018` |
| Alpha Architect | alpha architect | [alpha-architect.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/BOXX.png) | 2,001 | `49c1b2c08871aac008431e52781d27a56ce8279a91cbc35eaa01b222b58936cd` |
| American Century Investments | american century, avantis | [american-century.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/FLV.png) | 20,338 | `47d059b30ef588b1a63e8ffc61e384af8ed479c8f20a5dcd538a296e2c053314` |
| Amplify ETFs | amplify | [amplify.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/DIVO.png) | 2,501 | `d4e0f7346bc7cc267f4fd21355fb8dd5e1e860b1a18975f2c3b25f158d324bc8` |
| BlackRock / iShares | ishares, blackrock | [blackrock.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/BLK.png) | 5,612 | `dd10f38629b54545d6bc97f7cfe86b392756b015c5884f5214c7b38f67bb5127` |
| Capital Group | capital group | [capital-group.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/CGUS.png) | 341 | `44750089f3ec1e9914d3959d3e2aede5c23613463d78c5dd5b69474fd626d89a` |
| Charles Schwab | schwab, charles schwab | [schwab.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/SCHB.png) | 1,678 | `7911fab32e528cd07f97c0d2a0a52ff4614889ebd558e1bcd885919944292e0f` |
| Dimensional Fund Advisors | dimensional, dfa | [dimensional.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/DFAC.png) | 10,279 | `7e167fcee73439d529b72da6abfcf9c4096d57e60286f18dfa1a76a0bb8cece4` |
| Direxion | direxion | [direxion.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/SPXL.png) | 4,121 | `a7a7e59fd1a78986f6d97d0bf91dc41bc859e9ccf2fa36bdd9b581d2683c6072` |
| Fidelity Investments | fidelity | [fidelity.png](https://github.com/SolarSistim/Quickdash/blob/0bfa714464a7181c615b09d052cb538564e1f119/public/assets/icons/fidelity_investment.png) | 15,223 | `c430fc88b7fa5adf2fb46997fd6b3a30dfce565eb369dd8c681331a7bee43f34` |
| First Trust | first trust, ft vest, ft cboe vest | [first-trust.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/FTCS.png) | 4,489 | `67e25773e6e4f3e72a33b5ef014d0609d360c06d36f5db099f7c9fadcf0084b8` |
| Franklin Templeton | franklin, templeton, legg mason, clearbridge | [franklin-templeton.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/BEN.png) | 3,189 | `043592183ff82351d2c4ae00ed2c896bd3e4e79509ec2d0484b522d0c322cea2` |
| Global X | global x, globalx | [global-x.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/QYLD.png) | 5,869 | `ed98c29fc4a619a5dd248cb014711123e20e7a307e5633d02c246cf5de05cefd` |
| Goldman Sachs | goldman sachs, goldman | [goldman-sachs.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/GS.png) | 8,735 | `41c3a16663a886ec4859bbb593558cc49bff952bbc9201446037f8442bf2dde9` |
| Harbor Capital | harbor | [harbor.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/HGER.png) | 7,386 | `7bc998a05076eb3ea159ddf3aca1ac7fd43ecf9022201e7fa9cce14c63efcb4a` |
| Innovator | innovator | [innovator.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/PJAN.png) | 1,383 | `b70075883608f14d1b02b1b2a095c1b4a86eff2ddf9f3a2d5be5156f5e5fa3ea` |
| Invesco | invesco, powershares | [invesco.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/QQQ.png) | 7,396 | `5a9275b97ee2e7162e25db7d665c92879a9227f914253981a72597dd0da2cbf3` |
| J.P. Morgan | jpmorgan, jp morgan, j p morgan | [jpmorgan.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/JEPI.png) | 6,725 | `b300c027042b959f36f6d74e3f90ef19b2f0119e2b12ae025cd1b0948c5a8072` |
| Janus Henderson | janus henderson, janus | [janus-henderson.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/JAAA.png) | 2,383 | `829e42dc292f0893c435ec6e10e78029bb78a22205c07cbcac9685e2ff273888` |
| PGIM / Prudential | pgim, prudential | [pgim.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/PULS.png) | 3,226 | `a9d43cbfe82bc4c19e6a6cae8733fbe34b259530f11a3d6620968decad6882bc` |
| PIMCO | pimco | [pimco.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/BOND.png) | 1,919 | `ffe8ff2f9ff569a0ffe3cae149a38a64e00ef8ad9ee89f11594bf4c93136a8cd` |
| Pacer | pacer | [pacer.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/COWZ.png) | 2,691 | `55f12997eee3f942137512d9778805b69a2e4391a2813e3f3a4cee3ed4600340` |
| ProShares | proshares | [proshares.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/TQQQ.png) | 3,162 | `6d2f127f62f4ec24f9e6a229aaa24563199f8f0d9a0e89cc384a01205a8fb6a9` |
| Roundhill Investments | roundhill | [roundhill.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/MAGS.png) | 3,660 | `5790ab094f75136cce953d91e9e1ed5fb305a6b3aaf6dc48cba31bb35180ca5e` |
| State Street | state street, spdr, ssga | [state-street.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/SPY.png) | 7,068 | `63237619737ff5a64a42adde9aed1c39d2f6d9efecc569b6b04c0135d40e4c0f` |
| T. Rowe Price | t rowe price | [t-rowe-price.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/TROW.png) | 11,635 | `1de36e6b1082d352466438a4d136d9a09479919940bda5b3f8652d9ce7a2034c` |
| VanEck | vaneck, van eck | [vaneck.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/SMH.png) | 7,947 | `f20ab60bd054350de8986e4ce7abe5adcabf794a4fec5c5c903af0ec5817148b` |
| Vanguard | vanguard | [vanguard.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/VOO.png) | 6,337 | `e36ac3112693e4266fd79777985c5259da43d68ae01082e62d9e1ffd18511431` |
| WisdomTree | wisdomtree, wisdom tree | [wisdomtree.png](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/USFR.png) | 12,560 | `b4d671c28969a41c92932dd753283345f7f62e0b29e966f58ca3cc39dd854d2d` |

DBS: [source PNG](https://github.com/tdrmk/stock-icons/blob/e88424652fb4e41776144ba0e0f837659818ede9/ticker_icons/DBSDF.png), 8,193 bytes; SHA-256 `ded26151978a3568abcb6878999ca8265dced93e26ece9b2761994b376f32e37`.

## Cache and identification

Existing cached identities with an empty logo gain the local image through ticker/name lookup; no history deletion or redownload is required. Fresh search results retain instrument type and the recognized issuer ID. Known ETF symbols and provider-name prefixes identify logos; an unknown fund is not assigned an invented brand. Equity identities are kept distinct from ETF providers.

Colours and logos are portable Python/SQLite metadata and PNG resources for Android and future iOS builds. No OS-specific paths or device IDs are stored.
