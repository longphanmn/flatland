"""Localization data for /wiki and /api/wiki in English, Vietnamese, and French.

Provides translations for UI chrome, articles, book comparisons, sustainability,
performance documentation, and GodLaws parameter hints.
"""

from __future__ import annotations

SUPPORTED_LANGS = ("en", "vi", "fr")
DEFAULT_LANG = "en"


def normalize_lang(lang: str | None) -> str:
    """Normalize a language code or Accept-Language header to 'en', 'vi', or 'fr'."""
    if not lang:
        return DEFAULT_LANG
    lang = lang.lower().strip()
    if lang.startswith("vi"):
        return "vi"
    if lang.startswith("fr"):
        return "fr"
    if lang.startswith("en"):
        return "en"
    return DEFAULT_LANG


# ---------------------------------------------------------------------
# UI Chrome Translations (header, nav, search, card, badges, footer)
# ---------------------------------------------------------------------
UI_I18N = {
    "en": {
        "title": "Flatland — Living Wiki — World Simulation by Long Phan",
        "description": "Official living wiki and system encyclopedia for Flatland: 2D autonomous World Simulation by Long Phan (long@minhnhan.in).",
        "og_title": "Flatland — Living Wiki | World Simulation by Long Phan",
        "og_desc": "Official living wiki, presets, and mechanics documentation for Flatland World Simulation by Long Phan (long@minhnhan.in).",
        "wiki_heading": "📖 Flatland Wiki & Guide",
        "search_placeholder": "Search laws, routes, docs… ( / )",
        "swagger_docs": "Swagger /docs",
        "openapi": "OpenAPI",
        "guide": "Guide",
        "json_api": "JSON",
        "live_world": "← Live world",
        "presets_label": "Presets:",
        "dev_by": "Developed by",
        "dev_name": "Long Phan",
        "built_with": "Built with OpenCode & Antigravity<br/>Inspired by Edwin A. Abbott",
        "badge_laws": "{laws} laws",
        "badge_routes": "{routes} routes",
        "badge_presets": "{presets} presets",
        "sphere_motto": "The Sphere sets laws, never a life",
        "guide_link": "Guide",
        "footer": "Generated from live code — <code>Config</code> defaults + <code>GodLaws</code> + <code>app.routes</code>. Official living documentation & encyclopedia for Flatland. · Developed by <strong>Long Phan</strong> — <a href=\"mailto:long@minhnhan.in\">long@minhnhan.in</a> · <a href=\"https://minhnhan.in\">minhnhan.in</a> · Built with OpenCode & Antigravity",
        "preset_col_name": "Preset",
        "preset_col_laws": "Key laws",
        "preset_col_apply": "Apply",
        "preset_via_app": "Via the app UI or TUI",
        "preset_sidebar_note": "Read-only here — apply presets in the app UI or TUI.",
        "active_badge": "ACTIVE",
        "api_ref_title": "# API reference\n\nLive routes from `app.routes` + Swagger at [/docs](/docs). Try `curl` examples below.",
        "laws_title": "# Laws of the Sphere\n\nEvery law in `GodLaws` (`protocol.py:108`) with type/range/default. Set via `POST /api/laws` or presets.",
        "presets_title": "# Presets — one-click worlds\n\nSustainable is the 1000-day gentle world. Apply via The Sphere panel or `POST /api/presets/{name}?reset`.",
        "roadmap_title": "Roadmap",
        "roadmap_desc": "# Roadmap\n\nSee `TODO.md` (active) + `docs/roadmap-archive.md` (completed) — {sections} sections + {laws} laws + {routes} routes + {presets} presets. Wiki extends Guide with presets, sustainability & playground.",
        "law_col_law": "Law",
        "law_col_type": "Type",
        "law_col_range": "Range",
        "law_col_default": "Default",
        "law_col_hint": "Hint + docs",
        "route_col_method": "Method",
        "route_col_path": "Path",
        "route_col_name": "Name",
        "route_col_desc": "Description",
        "curl_title": "## Curl playground",
        "nav_group_core": "Core Knowledge",
        "nav_group_systems": "Systems & Balance",
        "nav_group_reference": "Rules & Reference",
        "live_pulse": "Live World",
    },
    "vi": {
        "title": "Flatland — Bách khoa toàn thư Wiki — Mô phỏng Thế giới bởi Long Phan",
        "description": "Tài liệu bách khoa toàn thư và wiki sống chính thức của Flatland: Hệ thống mô phỏng thế giới tự trị 2D phát triển bởi Long Phan (long@minhnhan.in).",
        "og_title": "Flatland — Living Wiki | Hệ thống Mô phỏng Thế giới bởi Long Phan",
        "og_desc": "Tài liệu chính thức về cơ chế mô phỏng, cấu hình mẫu và các định luật tự nhiên của Flatland bởi Long Phan (long@minhnhan.in).",
        "wiki_heading": "📖 Bách khoa toàn thư Flatland",
        "search_placeholder": "Tìm kiếm định luật, API, tài liệu… ( / )",
        "swagger_docs": "Swagger /docs",
        "openapi": "OpenAPI",
        "guide": "Cẩm nang",
        "json_api": "Dữ liệu JSON",
        "live_world": "← Thế giới trực tiếp",
        "presets_label": "Cấu hình mẫu:",
        "dev_by": "Phát triển bởi",
        "dev_name": "Long Phan",
        "built_with": "Xây dựng với OpenCode & Antigravity<br/>Lấy cảm hứng từ Edwin A. Abbott",
        "badge_laws": "{laws} định luật",
        "badge_routes": "{routes} tuyến API",
        "badge_presets": "{presets} cấu hình",
        "sphere_motto": "The Sphere ban hành định luật, không can thiệp số mệnh",
        "guide_link": "Cẩm nang",
        "footer": "Tự động sinh từ mã nguồn thực tế — <code>Config</code> + <code>GodLaws</code> + <code>app.routes</code>. Bách khoa toàn thư và tài liệu sống chính thức của Flatland. · Phát triển bởi <strong>Long Phan</strong> — <a href=\"mailto:long@minhnhan.in\">long@minhnhan.in</a> · <a href=\"https://minhnhan.in\">minhnhan.in</a> · Xây dựng với OpenCode & Antigravity",
        "preset_col_name": "Cấu hình",
        "preset_col_laws": "Các luật trọng tâm",
        "preset_col_apply": "Áp dụng",
        "preset_via_app": "Qua app hoặc TUI",
        "preset_sidebar_note": "Chỉ xem tại đây — hãy áp dụng trong app hoặc TUI.",
        "active_badge": "ĐANG DÙNG",
        "api_ref_title": "# Tham chiếu API\n\nDanh sách tuyến API trực tiếp từ `app.routes` + tài liệu tương tác tại [/docs](/docs). Xem các ví dụ lệnh `curl` bên dưới.",
        "laws_title": "# Các Định luật của Thượng đế (The Sphere)\n\nTất cả các trường `GodLaws` (`protocol.py:108`) — kiểu dữ liệu, phạm vi và giá trị mặc định. Thay đổi qua `POST /api/laws` hoặc chọn cấu hình mẫu.",
        "presets_title": "# Cấu hình mẫu — Khởi tạo thế giới 1-chạm\n\n'sustainable' là thế giới hưng thịnh hòa bình 1000 ngày. Áp dụng qua bảng The Sphere hoặc lệnh `POST /api/presets/{name}?reset`.",
        "roadmap_title": "Lộ trình phát triển",
        "roadmap_desc": "# Lộ trình phát triển\n\nXem `TODO.md` (đang mở) + `docs/roadmap-archive.md` (đã hoàn thành) — {sections} phần + {laws} định luật + {routes} tuyến API + {presets} cấu hình mẫu. Wiki mở rộng Guide với các preset, tính bền vững & công cụ thử nghiệm.",
        "law_col_law": "Định luật",
        "law_col_type": "Kiểu",
        "law_col_range": "Khoảng",
        "law_col_default": "Mặc định",
        "law_col_hint": "Gợi ý & tài liệu",
        "route_col_method": "Phương thức",
        "route_col_path": "Đường dẫn",
        "route_col_name": "Tên hàm",
        "route_col_desc": "Mô tả",
        "curl_title": "## Công cụ dòng lệnh Curl",
        "nav_group_core": "Tri thức Cốt lõi",
        "nav_group_systems": "Hệ thống & Cân bằng",
        "nav_group_reference": "Định luật & Tham chiếu",
        "live_pulse": "Thế giới Trực tiếp",
    },
    "fr": {
        "title": "Flatland — Wiki Vivant — Simulation de Monde par Long Phan",
        "description": "Wiki vivant officiel et encyclopédie du système Flatland : Simulation de monde autonome en 2D par Long Phan (long@minhnhan.in).",
        "og_title": "Flatland — Wiki Vivant | Simulation de Monde par Long Phan",
        "og_desc": "Documentation officielle du wiki, des préréglages et des mécaniques de la simulation Flatland par Long Phan (long@minhnhan.in).",
        "wiki_heading": "📖 Encyclopédie Flatland",
        "search_placeholder": "Rechercher des lois, routes API, docs… ( / )",
        "swagger_docs": "Swagger /docs",
        "openapi": "OpenAPI",
        "guide": "Guide",
        "json_api": "Données JSON",
        "live_world": "← Monde en direct",
        "presets_label": "Préréglages :",
        "dev_by": "Développé par",
        "dev_name": "Long Phan",
        "built_with": "Conçu avec OpenCode & Antigravity<br/>Inspiré par Edwin A. Abbott",
        "badge_laws": "{laws} lois",
        "badge_routes": "{routes} routes API",
        "badge_presets": "{presets} préréglages",
        "sphere_motto": "La Sphère dicte les lois, jamais une vie",
        "guide_link": "Guide",
        "footer": "Généré à partir du code source en temps réel — Valeurs <code>Config</code> + <code>GodLaws</code> + <code>app.routes</code>. Documentation vivante officielle et encyclopédie de Flatland. · Développé par <strong>Long Phan</strong> — <a href=\"mailto:long@minhnhan.in\">long@minhnhan.in</a> · <a href=\"https://minhnhan.in\">minhnhan.in</a> · Conçu avec OpenCode & Antigravity",
        "preset_col_name": "Préréglage",
        "preset_col_laws": "Lois fondamentales",
        "preset_col_apply": "Appliquer",
        "preset_via_app": "Via l'app ou le TUI",
        "preset_sidebar_note": "Lecture seule ici — appliquez via l'app ou le TUI.",
        "active_badge": "ACTIF",
        "api_ref_title": "# Référence de l'API\n\nRoutes en direct issues de `app.routes` + documentation Swagger à [/docs](/docs). Essayez les exemples `curl` ci-dessous.",
        "laws_title": "# Lois de la Sphère (The Sphere)\n\nTous les champs de `GodLaws` (`protocol.py:108`) — type, plage et valeur par défaut. Modifiables via `POST /api/laws` ou par préréglage.",
        "presets_title": "# Préréglages — Mondes prêts en un clic\n\n'sustainable' offre une paix durable de 1000 jours. Appliquez via le panneau La Sphère ou `POST /api/presets/{name}?reset`.",
        "roadmap_title": "Feuille de route",
        "roadmap_desc": "# Feuille de route\n\nVoir `TODO.md` (actif) + `docs/roadmap-archive.md` (terminé) — {sections} sections + {laws} lois + {routes} routes + {presets} préréglages. Le Wiki enrichit le Guide avec les préréglages, la durabilité & les tests.",
        "law_col_law": "Loi",
        "law_col_type": "Type",
        "law_col_range": "Plage",
        "law_col_default": "Défaut",
        "law_col_hint": "Indice & docs",
        "route_col_method": "Méthode",
        "route_col_path": "Chemin",
        "route_col_name": "Nom",
        "route_col_desc": "Description",
        "curl_title": "## Exemples de requêtes Curl",
        "nav_group_core": "Connaissances de Base",
        "nav_group_systems": "Systèmes & Équilibre",
        "nav_group_reference": "Lois & Référence",
        "live_pulse": "Monde en Direct",
    },
}


# ---------------------------------------------------------------------
# Navigation Section Slugs and Titles with Categories and Icons
# ---------------------------------------------------------------------
NAV_SECTIONS = [
    # Core Knowledge
    ("overview", {"en": "Overview", "vi": "Tổng quan", "fr": "Aperçu"}, "core", "📖"),
    ("book-comparison", {"en": "Flatland Book vs Simulation", "vi": "Sách Flatland vs Mô phỏng", "fr": "Livre Flatland vs Simulation"}, "core", "📐"),
    ("quickstart", {"en": "Quickstart", "vi": "Bắt đầu nhanh", "fr": "Démarrage rapide"}, "core", "⚡"),
    ("how-the-world-works", {"en": "How the world works", "vi": "Nguyên lý vận hành", "fr": "Fonctionnement du monde"}, "core", "⚙️"),

    # Systems & Balance
    ("sustainability", {"en": "Sustainability", "vi": "Tính bền vững & Cân bằng", "fr": "Durabilité & Équilibre"}, "systems", "🌿"),
    ("performance", {"en": "Performance & Scale", "vi": "Hiệu năng & Quy mô", "fr": "Performance & Échelle"}, "systems", "🚀"),
    ("codebase-map", {"en": "Codebase map", "vi": "Bản đồ mã nguồn", "fr": "Carte du code source"}, "systems", "🗺️"),
    ("data-model-protocol", {"en": "Data model & protocol", "vi": "Mô hình dữ liệu & Giao thức", "fr": "Modèle de données & Protocole"}, "systems", "💾"),

    # Laws & Reference
    ("god-laws", {"en": "Laws of the Sphere", "vi": "Các định luật của Chúa", "fr": "Lois de la Sphère"}, "reference", "⚖️"),
    ("presets", {"en": "Presets", "vi": "Cấu hình mẫu", "fr": "Préréglages"}, "reference", "🎯"),
    ("api-reference", {"en": "API reference", "vi": "Tham chiếu API", "fr": "Référence de l'API"}, "reference", "🔌"),
    ("configuration-ops", {"en": "Configuration & ops", "vi": "Cấu hình & Vận hành", "fr": "Configuration & Exploitation"}, "reference", "🛠️"),
]


# ---------------------------------------------------------------------
# Articles Markdown Content
# ---------------------------------------------------------------------
WIKI_OVERVIEW_MD_I18N = {
    "en": r"""
# Flatland Wiki & Encyclopedia

> **Developed by [Long Phan](mailto:long@minhnhan.in)** ([long@minhnhan.in](mailto:long@minhnhan.in) · [minhnhan.in](https://minhnhan.in) · [world.minhnhan.in](https://world.minhnhan.in))  
> Built and refined using **OpenCode** and **Antigravity** · Developed from the core ideas of **Edwin A. Abbott's *Flatland: A Romance of Many Dimensions*** (1884).

Flatland is an autonomous 2D artificial life and world simulation developed from the foundational mathematical and spatial ideas of Edwin A. Abbott's 1884 classic *Flatland*. 

### Design Philosophy
This project is **developed from the Flatland idea rather than mimicking the book literally**. It adopts Abbott's core premises — 2D planar constraints, geometric vertex hierarchies, atmospheric perception, and higher-dimensional observation — as a foundation to create a **living, evolutionary artificial life ecosystem that organically changes and expands over time**.

### Core Architecture & Systems
- **The Sphere (God Model)**: The Sphere (God) sets global **laws of nature** (carrying capacity, food growth, metabolism, disease, climate) from Spaceland, never intervening in individual lives. Configured via a dedicated **🎯 Presets** selector and 6 streamlined **⚖️ Macro Domains** with live search and dual sliders. Organisms navigate continuously via 16-sensor raycasts and Micro-RNN neural actuators.
- **Botanical Ecology & Functional Nutrition**: 6 diverse plant species (`grass`, `grain`, `berry`, `medicinal_herb`, `mushroom`, `poisonous`) with distinct caloric densities, decay clocks, infection remedy effects, and targeted health-based foraging preferences.
- **Cognitive Agency & Clan Social Intelligence**: Multi-objective utility AI replaces rigid if/else trees (evaluating survival, duty, traits, and kin needs); spatial waypoint mental maps; tactical soldier phalanxes, line kiting maneuvers, interpersonal trust-based buddy pairing, autonomous clan task boards (dynamic labor division), governance archetypes (Monarchy, Theocracy, Junta, Republic), adaptive bylaws (winter rationing, martial law), calculated Casus Belli, inter-clan trade caravans, and annual autumn harvest festivals.
- **Autonomous Evolution & Culture**: 6 heritable personality archetypes (`brave`, `cautious`, `altruistic`, `greedy`, `explorer`, `builder`), craftable tools (spears, baskets, herb poultices, chieftain crowns), 4 mastery skills (Farming 🌾, Combat ⚔️, Foraging 🦴, Healing 🌿), earned dynamic titles, oral lore passed from elders to youth in houses, and live thought bubbles.
- **Realistic Energy & Metabolism**: Infant low metabolism ($0.45\times$ energy decay), combat stamina expenditure, and autonomous field food reserve management via baskets.
- **Settlements & Diplomacy**: Walled houses with creature-sized doors, multi-house clan territories, settlement food larders, mutual coalitions, tributary pacts, and schisms.
- **Geometric Physics & Morphological Evolution (K∈[3,24])**: Polar genomes $(r_i,\phi_i)$ $K\in[3,24]$ (`KMAX 24`, `morphology_engine.py`) with SoA `physical_traits` trait baking ($A,P,I_{zz},\theta_{\min},asym,D_{mult}$) and SAT narrowphase (broadphase $r_{\max}$ + circle fallback $K\ge24$ & $asym<0.05$ + edge normals); annealing $\lambda(g)$ blends Abbott templates → free evolution, energetic asymmetry, neural courtship, and extinction safeguards ($\eta(N)$, Tier1/2/3 genesis, mercy).
- **Real-Time Synchronization**: Deterministic fixed-rate engine loop streaming state over WebSocket (`/ws`) at ~30–60 FPS with durable SQLite historical chronicle storage.
""",
    "vi": r"""
# Bách khoa toàn thư & Wiki Flatland

> **Phát triển bởi [Long Phan](mailto:long@minhnhan.in)** ([long@minhnhan.in](mailto:long@minhnhan.in) · [minhnhan.in](https://minhnhan.in) · [world.minhnhan.in](https://world.minhnhan.in))  
> Xây dựng và hoàn thiện bằng **OpenCode** & **Antigravity** · Phát triển từ ý tưởng cốt lõi trong tác phẩm kinh điển ***Flatland: A Romance of Many Dimensions*** (1884) của **Edwin A. Abbott**.

Flatland là một thế giới mô phỏng sự sống nhân tạo 2D tự trị, được phát triển từ các tiền đề toán học và không gian trong cuốn sách kinh điển *Flatland* (Xứ Phẳng) xuất bản năm 1884 của Edwin A. Abbott.

### Triết lý thiết kế
Dự án này được **phát triển từ ý niệm của Xứ Phẳng thay vì mô phỏng máy móc từng chi tiết trong cuốn sách**. Hệ thống kế thừa các tiền đề cốt lõi của Abbott — các giới hạn trong mặt phẳng 2D, đẳng cấp dựa trên số đỉnh hình học, nhận thức thị giác trong khí quyển và góc nhìn quan sát từ chiều không gian cao hơn — làm nền móng để kiến tạo một **hệ sinh thái sự sống nhân tạo tiến hóa sống động, tự thích nghi và phát triển hữu cơ theo thời gian**.

### Kiến trúc & Các hệ thống cốt lõi
- **The Sphere (Mô hình Thượng đế)**: The Sphere (Khối Cầu) thiết lập các **định luật của tự nhiên** (sức chứa môi trường, tốc độ sinh trưởng thực vật, trao đổi chất, dịch bệnh, khí hậu) từ Spaceland (Không Gian 3 Chiều), hoàn toàn không can thiệp vi mô vào từng cá thể. Được cấu hình thông qua **🎯 Cấu hình mẫu (Presets)** và 6 **⚖️ Lĩnh vực Vĩ mô** với thanh trượt kép và tìm kiếm trực tiếp. Sinh vật định hướng liên tục qua 16 cảm biến tia và mạng nơ-ron Micro-RNN.
- **Sinh thái thực vật & Dinh dưỡng chức năng**: 6 loài thực vật đa dạng (`cỏ`, `ngũ cốc`, `quả mọng`, `thảo dược`, `nấm`, `độc thảo`) với mật độ calo riêng biệt, đồng hồ phân hủy, dược tính trị bệnh và hành vi tìm kiếm thức ăn thông minh dựa trên trạng thái sức khỏe.
- **Trí tuệ nhận thức & Xã hội bộ tộc**: AI thỏa dụng đa mục tiêu thay thế hoàn toàn các cây lệnh rẽ nhánh cứng nhắc; bản đồ tinh thần điểm mốc không gian; đội hình phalanx của binh sĩ, chiến thuật thả diều của nữ giới (đoạn thẳng), kết bạn tin cậy đôi bạn cùng tiến, bảng phân công lao động bộ tộc tự trị, các thể chế chính trị (Quân chủ, Thần quyền, Quân phiệt, Cộng hòa), luật lệ thích ứng (chia khẩu phần mùa đông, thiết quân luật), cớ tuyên chiến (Casus Belli), các đoàn buôn liên bộ tộc và lễ hội thu hoạch mùa thu hàng năm.
- **Tiến hóa tự trị & Văn hóa**: 6 hình mẫu tính cách di truyền (`dũng cảm`, `thận trọng`, `vị tha`, `tham lam`, `thám hiểm`, `thợ xây`), công cụ chế tạo (giáo, giỏ đựng, thuốc đắp, vương miện thủ lĩnh), 4 kỹ năng tinh thông (Nông nghiệp 🌾, Chiến đấu ⚔️, Thu lượm 🦴, Y thuật 🌿), danh hiệu động đạt được qua chiến công, truyền khẩu tri thức từ người già sang thế hệ trẻ trong nhà, và bong bóng suy nghĩ trực quan.
- **Năng lượng & Trao đổi chất thực tế**: Ấu trùng có mức tiêu hao năng lượng thấp ($0.45\times$), thể lực tiêu hao trong giao tranh, và quản lý dự trữ lương thực cá nhân thông qua giỏ đeo.
- **Khu định cư & Ngoại giao**: Nhà có tường bao quanh với cửa ra vào chuẩn kích thước cơ thể, lãnh thổ bộ tộc đa nhà ở, kho lương thực chung, liên minh phòng thủ tương trợ, cống nạp và phân rã bộ tộc khi quá tải.
- **Vật lý hình học & Tiến hóa hình thái (K∈[3,24])**: Bộ gen cực $(r_i,\phi_i)$ $K\in[3,24]$ (`KMAX 24`, `morphology_engine.py`) với tính toán đặc tính thể chất SoA ($A,P,I_{zz},\theta_{\min},asym,D_{mult}$) và va chạm đa giác SAT thu hẹp; ủ nhiệt hình thái $\lambda(g)$ dung hòa giữa khuôn mẫu Abbott truyền thống và tiến hóa tự do, phối ngẫu nơ-ron, và các cơ chế bảo vệ khỏi tuyệt chủng ($\eta(N)$, Phép màu Khởi nguyên Cấp 1/2/3).
- **Đồng bộ hóa thời gian thực**: Vòng lặp mô phỏng xác định truyền phát trạng thái thế giới qua WebSocket (`/ws`) ở tốc độ ~30–60 FPS cùng kho lưu trữ biên niên sử bền vững SQLite.
""",
    "fr": r"""
# Encyclopédie & Wiki Flatland

> **Développé par [Long Phan](mailto:long@minhnhan.in)** ([long@minhnhan.in](mailto:long@minhnhan.in) · [minhnhan.in](https://minhnhan.in) · [world.minhnhan.in](https://world.minhnhan.in))  
> Conçu et perfectionné avec **OpenCode** & **Antigravity** · Développé à partir des concepts fondamentaux de l'œuvre classique d'**Edwin A. Abbott, *Flatland: A Romance of Many Dimensions*** (1884).

Flatland est une simulation autonome de vie artificielle et d'écosystème en 2D, conçue d'après les idées mathématiques et spatiales d'Edwin A. Abbott.

### Philosophie de conception
Ce projet est **développé à partir de l'idée de Flatland plutôt que d'imiter servilement le livre**. Il adopte les postulats d'Abbott — contraintes du plan 2D, hiérarchie géométrique selon le nombre de sommets, perception atmosphérique et regard depuis une dimension supérieure — pour fonder un **écosystème de vie artificielle évolutif et organique qui se métamorphose au fil du temps**.

### Architecture et systèmes fondamentaux
- **La Sphère (Modèle divin)** : La Sphère établit les **lois universelles de la nature** (capacité de charge, croissance végétale, métabolisme, maladies, climat) depuis Spaceland (l'espace tridimensionnel), sans jamais intervenir arbitrairement dans les existences individuelles. Paramétrable via un sélecteur de **🎯 Préréglages** et 6 **⚖️ Domaines Macro** avec recherche en temps réel et doubles curseurs. Les organismes se repèrent grâce à 16 capteurs de rayons et des actionneurs neuronaux Micro-RNN.
- **Écologie botanique & Nutrition fonctionnelle** : 6 espèces végétales distinctes (`herbe`, `grain`, `baie`, `herbe_médicinale`, `champignon`, `toxique`) dotées de densités caloriques propres, de cycles de flétrissement, d'effets curatifs et d'orientations alimentaires selon l'état de santé.
- **Agence cognitive & Intelligence sociale des clans** : Une IA d'utilité multi-objectifs remplace les arbres conditionnels rigides ; cartographie mentale par jalons spatiaux ; phalanges tactiques de soldats, manœuvres d'évitement des femmes-lignes, formation de binômes de confiance, tableaux de tâches claniques autonomes, régimes politiques variés (Monarchie, Théocratie, Junte, République), décrets d'urgence (rationnement hivernal, loi martiale), caravanes de commerce et fêtes automnales des moissons.
- **Évolution autonome & Culture** : 6 archétypes de personnalité héréditaires (`brave`, `prudent`, `altruiste`, `avare`, `explorateur`, `bâtisseur`), fabrication d'outils (lances, paniers, cataplasmes, couronnes), 4 compétences d'élite (Agriculture 🌾, Combat ⚔️, Cueillette 🦴, Soins 🌿), titres honorifiques dynamiques, transmission orale des aînés aux jeunes dans les demeures et bulles de pensées en direct.
- **Métabolisme & Dynamique énergétique réalistes** : Faible dépense chez les nouveau-nés ($0.45\times$), coût d'endurance au combat et gestion de réserves portatives via des paniers.
- **Colonies & Diplomatie** : Bâtisses closes avec portes ajustées, territoires multi-maisons, greniers communautaires, coalitions de défense mutuelle, tributs et scissions claniques.
- **Physique géométrique & Évolution morphologique (K∈[3,24])** : Génomes polaires $(r_i,\phi_i)$ $K\in[3,24]$ (`KMAX 24`, `morphology_engine.py`) avec calcul des propriétés physiques SoA ($A,P,I_{zz},\theta_{\min},asym,D_{mult}$) et détection fine SAT ; le recuit morphologique $\lambda(g)$ assure la transition des gabarits d'Abbott vers une spéciation libre, parade nuptiale neuronale et sauvegardes contre l'extinction ($\eta(N)$, miracles de la Genèse).
- **Synchronisation en temps réel** : Moteur déterministe diffusant l'état du monde via WebSocket (`/ws`) à ~30–60 FPS avec persistance historique sur SQLite.
""",
}

SUSTAINABILITY_MD_I18N = {
    "en": r"""
# Sustainability — Multi-Generational Balance

The world self-balances across hundreds of days and multi-generational dynastic flourishing under tuned ecological and social equilibrium.

## Curated Presets

- **balance** ⚖️ (Default) — Goldilocks harmony tuned for **200–350 inhabitants** with 380 food, carrying capacity 400 (max 500), gentle wars, rare predation, agriculture, density damping ($\xi$), extinction safeguards ($\eta$), and flourishing multi-generational clans.
- **sustainable** 🌿 — 1000-day prosperous peace: abundant food (550), carrying capacity 550 (max 600), rich granaries, harvest festivals, banquets, and gentle damping.
- **theocracy** 🔮 — Age of the Sphere: sacred avatars, glowing temples, avatar miracles, 3D epiphanies, holy synods, and divine tithes.
- **warlords** ⚔️ — Clash of clans: imperial conquests, granary raids, house takeovers, territorial expansion, and defensive coalitions.
- **chaos** 🔥 — High predator ratio, lethal wars, wildfires, earthquakes, frequent plagues, and fast seasonal turnover.
- **extinction** 💀 — Severe famine (120 food), harsh winter (0.30×), high exposure decay, testing societal resilience under collapse.
- **boom** 🚀 — High reproduction, 440 food, carrying capacity 800 (max 850) for monumental metropolis testing.

Use: `curl -X POST localhost:8000/api/presets/balance?reset=true` or use The Sphere (God Panel) preset selector.

## Dynamic Homeostasis & Extinction Prevention

Flatland includes two complementary closed-loop homeostatic feedback engines:

### 1. Density-Dependent Soft-Cap Damping ($\xi$)
When population $N$ exceeds carrying capacity $K_{cap}$, the overshoot ratio $\xi = (N - K_{cap}) / K_{cap}$ acts as a non-linear brake:
- **Birth Suppression**: $R_{birth} = R_0 / (1 + \text{damping\_steepness} \cdot \xi^2)$
- **Crowding Metabolic Stress**: $M_{decay} = M_0 \cdot (1 + \text{crowding\_stress\_mult} \cdot \xi)$
- **Resource Strain**: Plant growth and spread slow down proportionally to ecosystem saturation.

### 2. Extinction Safeguards & Genesis Miracles ($\eta$)
When population drops below $K_{safe} = K_{cap} \times \text{safeguard\_relief\_ratio}$, emergency relief kicks in:
- **Tier 1 ($\eta \le 0.5$)**: Famine relief, metabolic energy discount up to 40%, plant growth acceleration up to 60%.
- **Tier 2 ($\eta > 0.5$)**: Critical relief, reproduction cooldown halved, infant euthanasia suspended (`safeguard_morph_mercy`).
- **Tier 3 ($N \le K_{crit}$)**: The Sphere intervenes with a Genesis Miracle, creating `safeguard_genesis_batch` pristine regular beings to ensure species survival.
""",
    "vi": r"""
# Tính bền vững — Cân bằng sinh thái Đa thế hệ

Thế giới tự động duy trì sự cân bằng qua hàng trăm ngày và tạo điều kiện cho các dòng họ hưng thịnh qua nhiều thế hệ dưới trạng thái cân bằng sinh thái và xã hội hoàn chỉnh.

## Các cấu hình mẫu tuyển chọn (Presets)

- **balance** ⚖️ (Mặc định) — Trạng thái cân bằng vàng cho **200–350 cư dân** với 380 thức ăn, sức chứa 400 (tối đa 500), chiến tranh nhẹ nhàng, hiếm khi săn mồi ăn thịt, có nông nghiệp, hãm mật độ ($\xi$), cơ chế bảo vệ khỏi tuyệt chủng ($\eta$) và các bộ tộc đa thế hệ phát triển phồn vinh.
- **sustainable** 🌿 — Thái bình thịnh trị 1000 ngày: thức ăn dồi dào (550), sức chứa 550 (tối đa 600), kho lương thực trù phú, lễ hội mùa gặt, yến tiệc và hãm mật độ êm dịu.
- **theocracy** 🔮 — Kỷ nguyên Khối Cầu: tôn sùng các hóa thân linh thiêng, đền thờ rực sáng, phép màu hóa thân, hiển linh 3 chiều, công đồng tôn giáo và dâng nộp đức tin.
- **warlords** ⚔️ — Chiến tranh quân phiệt: các cuộc chinh phạt đế chế, cướp bóc kho lương, chiếm đoạt nhà cửa, bành trướng lãnh thổ và lập liên minh phòng thủ.
- **chaos** 🔥 — Tỷ lệ thú săn mồi cao, chiến tranh đẫm máu, cháy rừng, động đất, dịch bệnh thường xuyên và mùa vụ thay đổi dồn dập.
- **extinction** 💀 — Nạn đói khắc nghiệt (120 thức ăn), mùa đông giá buốt (0.30×), hao tổn ngoài trời cao, thử thách sức chống chịu của xã hội trước bờ vực diệt vong.
- **boom** 🚀 — Tỷ lệ sinh sản cực cao, 440 thức ăn, sức chứa 800 (tối đa 850) phục vụ thử nghiệm các siêu đô thị đông đúc.

Sử dụng: `curl -X POST localhost:8000/api/presets/balance?reset=true` hoặc chọn trên bảng điều khiển The Sphere.

## Cân bằng nội môi động & Phòng ngừa tuyệt chủng

Flatland tích hợp hai cơ chế phản hồi khép kín bổ trợ nhau để đảm bảo sự ổn định dài hạn:

### 1. Cơ chế hãm mềm phụ thuộc mật độ ($\xi$)
Khi dân số $N$ vượt quá sức chứa môi trường $K_{cap}$, tỷ lệ vượt ngưỡng $\xi = (N - K_{cap}) / K_{cap}$ đóng vai trò như chiếc phanh phi tuyến tính:
- **Kiềm chế sinh sản**: $R_{birth} = R_0 / (1 + \text{damping\_steepness} \cdot \xi^2)$
- **Áp lực trao đổi chất do chật chội**: $M_{decay} = M_0 \cdot (1 + \text{crowding\_stress\_mult} \cdot \xi)$
- **Căng thẳng tài nguyên**: Tốc độ sinh trưởng và phát tán của thực vật chậm lại tương ứng với mức độ bão hòa sinh thái.

### 2. Cơ chế cứu trợ diệt vong & Phép màu Khởi nguyên ($\eta$)
Khi dân số giảm xuống dưới ngưỡng an toàn $K_{safe} = K_{cap} \times \text{safeguard\_relief\_ratio}$, các tầng cứu trợ khẩn cấp sẽ kích hoạt:
- **Cấp 1 ($\eta \le 0.5$)**: Cứu trợ nạn đói, giảm mức tiêu hao năng lượng trao đổi chất tới 40%, đẩy nhanh tăng trưởng cây trồng lên tới 60%.
- **Cấp 2 ($\eta > 0.5$)**: Cứu trợ khẩn cấp, giảm một nửa thời gian hồi sinh sản, đình chỉ loại bỏ dị tật (`safeguard_morph_mercy`).
- **Cấp 3 ($N \le K_{crit}$)**: The Sphere can thiệp bằng Phép màu Khởi nguyên (Genesis Miracle), tạo ra `safeguard_genesis_batch` sinh vật hình học chính quy hoàn hảo để duy trì nòi giống.
""",
    "fr": r"""
# Durabilité — Équilibre Multi-Générationnel

Le monde maintient son équilibre sur des centaines de jours et permet l'essor de dynasties prospères grâce à une homéostasie écologique et sociale finement ajustée.

## Préréglages Sélectionnés

- **balance** ⚖️ (Défaut) — Équilibre idéal calibré pour **200 à 350 habitants** avec 380 unités de nourriture, capacité de 400 (max 500), guerres modérées, prédation rare, agriculture, amortissement de densité ($\xi$), sauvegarde contre l'extinction ($\eta$) et clans florissants.
- **sustainable** 🌿 — 1000 jours de paix prospère : nourriture abondante (550), capacité de charge 550 (max 600), greniers remplis, fêtes des moissons, banquets et amortissement doux.
- **theocracy** 🔮 — L'Ère de la Sphère : avatars sacrés, temples lumineux, miracles, épiphanies 3D, conciles sacrés et dîmes pieuses.
- **warlords** ⚔️ — L'affrontement des seigneurs : conquêtes impériales, pillages de greniers, prises de demeures, expansion territoriale et coalitions défensives.
- **chaos** 🔥 — Forte proportion de prédateurs, guerres meurtrières, incendies, séismes, épidémies fréquentes et saisons rapides.
- **extinction** 💀 — Famine sévère (120 nourriture), hivers rigoureux (0.30×), forte usure en extérieur, éprouvant la résistance sociétale face à l'effondrement.
- **boom** 🚀 — Reproduction effrénée, 440 nourriture, capacité de 800 (max 850) pour tester de gigantesques métropoles.

Utilisation : `curl -X POST localhost:8000/api/presets/balance?reset=true` ou via le panneau de La Sphère.

## Homéostasie Dynamique & Prévention de l'Extinction

Flatland intègre deux moteurs de rétroaction homéostatique en boucle fermée :

### 1. Amortissement Souple lié à la Densité ($\xi$)
Quand la population $N$ excède la capacité de charge $K_{cap}$, le ratio $\xi = (N - K_{cap}) / K_{cap}$ freine la surpopulation de façon non-linéaire :
- **Modération des naissances** : $R_{birth} = R_0 / (1 + \text{damping\_steepness} \cdot \xi^2)$
- **Stress métabolique de surpeuplement** : $M_{decay} = M_0 \cdot (1 + \text{crowding\_stress\_mult} \cdot \xi)$
- **Tension sur les ressources** : La régénération végétale ralentit proportionnellement à la saturation du milieu.

### 2. Sauvegardes d'Extinction & Miracles de la Genèse ($\eta$)
Lorsque la population chute sous le seuil d'alerte $K_{safe} = K_{cap} \times \text{safeguard\_relief\_ratio}$, des mesures d'urgence se déclenchent :
- **Niveau 1 ($\eta \le 0.5$)** : Secours anti-famine, dépense métabolique allégée jusqu'à 40%, accélération de la pousse végétale de 60%.
- **Niveau 2 ($\eta > 0.5$)** : Urgence critique, délai de reproduction réduit de moitié, suspension de l'euthanasie des difformes (`safeguard_morph_mercy`).
- **Niveau 3 ($N \le K_{crit}$)** : La Sphère opère un Miracle de la Genèse, créant un groupe `safeguard_genesis_batch` d'êtres réguliers pour perpétuer l'espèce.
""",
}

PERFORMANCE_MD_I18N = {
    "en": r"""
# Performance & Scale — 1000+ head @ 60 FPS

- **Zero-Allocation Spatial Hash**: Pre-allocated 1D bucket list in `world.py` eliminates tuple allocations and dictionary re-hashing per tick; `query_radius` uses squared-distance early-exit without `math.hypot`.
- **Fast Mate Discovery**: Spatial index queries nearby partners in $O(1)$ instead of $O(N^2)$ nested roster scans.
- **Snapshot Caching**: Static terrain and obstacles are pre-cached, eliminating redundant dictionary list copies on every broadcast frame.
- **Batched Canvas 2D Rendering**: Batches drawing passes by caste, plant variant, and house primitives with inline trigonometric vertex transforms, completely eliminating per-creature `ctx.save()` / `ctx.restore()` overhead (draw calls reduced from 20,000+ to ~30-50).
- **Dynamic Level of Detail (LOD)**: Zoom-dependent rendering skips fine-grained glyph text and ripples when zoomed out, maintaining 60 FPS even with dense populations.
- **Decoupled React State**: High-frequency simulation snapshots stream directly into mutable refs at 60 FPS for canvas rendering, while React virtual DOM reconciliation (HUD stats, charts) is throttled to ~6 Hz to keep the main browser thread light and responsive.
""",
    "vi": r"""
# Hiệu năng & Quy mô — Hơn 1000 cá thể @ 60 FPS

- **Bảng băm không gian không phân cấp (Zero-Allocation Spatial Hash)**: Danh sách ô 1 chiều cấp phát sẵn trong `world.py` loại bỏ việc tạo bộ tuple và băm lại từ điển mỗi tick; hàm `query_radius` so sánh khoảng cách bình phương thoát sớm không cần gọi `math.hypot`.
- **Tìm bạn tình siêu tốc**: Truy vấn đối tác tiềm năng lân cận qua chỉ mục không gian trong độ phức tạp $O(1)$ thay vì quét lồng nhau $O(N^2)$.
- **Bộ nhớ đệm ảnh chụp (Snapshot Caching)**: Địa hình tĩnh và chướng ngại vật được lưu sẵn vào bộ nhớ đệm, loại bỏ việc sao chép danh sách từ điển thừa thãi ở mỗi khung phát sóng.
- **Vẽ hàng loạt Canvas 2D (Batched Canvas 2D Rendering)**: Gộp các lượt vẽ theo giai cấp, biến thể thực vật và nhà ở với phép biến đổi góc lượng giác nội dòng, loại bỏ hoàn toàn chi phí `ctx.save()` / `ctx.restore()` cho từng sinh vật (lệnh vẽ giảm từ hơn 20.000 xuống còn ~30-50).
- **Độ chi tiết động (Dynamic LOD)**: Hiển thị phụ thuộc mức phóng to/thu nhỏ sẽ bỏ qua văn bản ký hiệu chi tiết và gợn sóng khi nhìn xa, duy trì độ mượt 60 FPS ổn định ngay cả với mật độ dân số dày đặc.
- **Tách biệt trạng thái React**: Dữ liệu mô phỏng tần số cao truyền thẳng vào các tham chiếu biến đổi (mutable refs) ở 60 FPS cho Canvas, trong khi giao diện React (thống kê HUD, đồ thị) được điều tiết ở tần số ~6 Hz giúp trình duyệt nhẹ nhàng và phản hồi tức thì.
""",
    "fr": r"""
# Performance & Échelle — Plus de 1000 individus @ 60 FPS

- **Hachage Spatial sans Allocation** : Une grille 1D pré-allouée dans `world.py` supprime les allocations de tuples et le re-hachage à chaque tick ; `query_radius` emploie un test de distance au carré sans `math.hypot`.
- **Recherche Rapide de Partenaires** : La recherche de partenaires via l'index spatial s'effectue en $O(1)$ au lieu d'un balayage quadratique $O(N^2)$.
- **Mise en Cache des Instantanés** : Le décor statique et les obstacles sont mis en cache, supprimant la duplication inutile de listes à chaque trame diffusée.
- **Rendu Groupé Canvas 2D** : Regroupement des passes de dessin par caste, plante et structure avec transformations trigonométriques directes, éliminant le coût de `ctx.save()` / `ctx.restore()` par individu (appels de tracé réduits de plus de 20 000 à ~30-50).
- **Niveau de Détail Dynamique (LOD)** : L'affichage adapte les détails selon le zoom (omission des glyphes fins en vue éloignée), assurant un 60 FPS constant même en forte densité.
- **État React Découplé** : Le flux haute fréquence alimente directement des références mutables à 60 FPS pour le Canvas, tandis que le rafraîchissement React (HUD, graphiques) est régulé à ~6 Hz pour préserver la fluidité de l'interface.
""",
}

FLATLAND_BOOK_COMPARISON_MD_I18N = {
    "en": r"""
# Flatland: The Novella vs. The Simulation

A comparative study between **Edwin A. Abbott’s 1884 satirical classic *Flatland: A Romance of Many Dimensions*** and this autonomous artificial life simulation.

---

## 1. Caste, Geometry & Social Hierarchy

| Dimension | Abbott’s Book (*Flatland*, 1884) | Our Application (*Flatland Simulator*) |
| :--- | :--- | :--- |
| **Hierarchy Principle** | *"Configuration makes the man."* Social status is strictly determined by the number of sides and regularity of angles. | Entities inherit exact geometric castes based on vertex count (N-gons) and regularity. |
| **Women (Lines)** | Straight lines with no angular width. Because they are practically invisible head-on and razor-sharp, they are legally required to make a continuous "peace cry" and use dedicated side doors. | Rendered as 1D segments (`shape: 'line'`). Distinct agility, movement, and domestic shelter dynamics. |
| **Working Class / Soldiers** | Isosceles triangles with narrow, sharp vertex angles (dangerous, volatile, prone to rebellions). | **Soldiers** (`#ff7b72`): Sharp combatants with boosted attack, military discipline, and perimeter defense behavior. |
| **Artisans & Middle Class** | Equilateral triangles (3 equal sides) — stable and respectable tradespeople. | **Artisans** (3–4 sides, `#f2cc60`): Farmers, foragers, and builders responsible for harvesting and maintaining houses. |
| **Gentlemen & Professionals** | Squares (4 sides) and Pentagons (5 sides) — the middle/upper administrative classes. | **Gentlemen** (4 sides, `#ffa657`) and **Professionals** (5 sides, `#d2a8ff`): Administrative and specialized roles. |
| **Nobility** | Hexagons (6 sides) and higher polygons — aristocrats and statesmen. | **Nobles** (6–8 sides, `#79c0ff`): High influence and lineage priority. |
| **Priesthood (Circles)** | Polygons with so many sides (≥ 24 to hundreds) that their vertices are imperceptible, forming smooth circles. They govern religion, law, and morality. | **Priests** (≥ 24 sides, `#e6edf3`): Emit soothing auras, heal injured or infected clanmates, and resist disease. |

---

## 2. The "Law of Nature" & Generational Ascent

- **In the Book**:
  - Abbott establishes the **"Law of Upward Development"**: A male child of a regular polygon almost always inherits **one more side** than his father (e.g., a Square fathers a Pentagon, whose son becomes a Hexagon), lifting the lineage toward circular Priesthood over generations.
  - Rare **"Irregulars"** (whose sides/angles do not match) are viewed as societal threats and sent to state institutions or executed.
- **In the App**:
  - **Generational Evolution**: Offspring inherit ancestral traits with a probabilistic side increment (`sides += 1`), simulating the gradual generational ascent toward circular perfection.
  - **Irregularity & Demotion**: Entities that develop genetic irregularity or undergo trauma have their irregularity tracked and are judged/demoted or marked with distinct visual indicators.
  - **Dynastic Lineage**: The Family Tree tracks mother, father, and generational pedigree across decades of world history.

---

## 3. Sight Recognition, Weather & Perception

- **In the Book**:
  - In a 2D world, all inhabitants look like flat lines from the edge!
  - In the **Foggy South**, Flatlanders rely on **"Sight Recognition"** — judging the angle and distance of an approaching polygon by how quickly its edges fade into the atmospheric fog.
  - In the **Clear North**, they must rely on **"Feeling"** (touching vertices with fingertips).
- **In the App**:
  - **Dynamic Weather Engine**: Simulates **Clear**, **Fog**, **Rain**, and **Storm** states.
  - **Atmospheric Vision**: Fog and storms dynamically restrict creature vision radii (`sight_radius`), forcing entities to rely on local spatial queries and nearby auditory alarms (`signals`).
  - **Day/Night & Lighting**: The ambient illuminance curves shift through dawn, noon, dusk, and pitch-black night, restricting wandering and driving creatures into their shelters.

---

## 4. Housing, Settlements & Territorial Architecture

- **In the Book**:
  - Houses are strictly pentagonal or hexagonal, with specific entrances: a smaller rear entrance for lines (women) and a main entrance for polygons.
- **In the App**:
  - **Settlement Economy**: Houses are physical 2D structures with precise interior boundaries, oriented doors (`north`, `east`, `south`, `west`), and bed capacities.
  - **Single Main House Invariant**: Each clan establishes exactly **one Main House / HQ** (the Leader's residence) with surrounding outpost shelters.
  - **Shelter Dynamics**: Creatures seek refuge inside houses to sleep at night, protect against winter frostbite, heal from chills, and educate infant offspring.
  - **Doorway Entry & Exit Navigation**: Creatures calculate vector standoff waypoints to transition smoothly through doorway openings when entering shelter at dusk or exiting to forage and explore at dawn, preventing indoor wall trapping.

---

## 5. Clan Diplomacy, Totems & Autonomous Society

While Abbott’s book portrays a centralized Victorian government, our app layers an **evolutionary social simulation**:
- **Tribal Totems & Specialization**: Clans worship distinct totems (🐺 Wolf, 🐻 Bear, 🦅 Eagle, 🦌 Stag, 🐍 Serpent, 🦉 Owl), shifting personality traits and societal balance between warriors, farmers, and scavengers.
- **Diplomacy, Tributes & War**: Dynamic clan relations with wars, peace treaties, tribute subjugation, and schisms.
- **Personal Autonomy & Inventory**: Independent personality archetypes (Brave, Cautious, Altruistic, Greedy, Explorer, Builder) with personal foraging baskets, tools (spears, crowns, herb poultices), and emergency self-preservation eating.

---

## 6. The Higher Dimension: The User as "The Sphere"

The most profound connection between the app and the book is the **role of the user**:
- In *Flatland*, the protagonist **A Square** is visited by **A Sphere** from the 3D *Spaceland*, who can look down from the Z-axis, see into locked rooms, view internal organs, and manipulate the 2D world with god-like omnipresence.
- **In our App**:
  - **You are the Sphere (God)**: As the observer on your screen, you look down on Flatland from Spaceland (the third dimension).
  - **The Sphere Panel**: You hold the power of The Sphere to alter the "Laws of Nature" in real-time — toggling famine, changing food growth multipliers, curing or spreading plagues, introducing winter freezes, or blessing clans with prosperity.
""",
    "vi": r"""
# Xứ Phẳng: Tiểu thuyết vs. Hệ thống Mô phỏng

Nghiên cứu đối chiếu giữa tiểu thuyết châm biếm kinh điển năm 1884 của **Edwin A. Abbott — *Flatland: A Romance of Many Dimensions*** và hệ sinh thái mô phỏng sự sống nhân tạo tự trị này.

---

## 1. Đẳng cấp, Hình học & Thứ bậc Xã hội

| Khía cạnh | Tiểu thuyết của Abbott (*Flatland*, 1884) | Ứng dụng Mô phỏng (*Flatland Simulator*) |
| :--- | :--- | :--- |
| **Nguyên lý thứ bậc** | *"Hình thù tạo nên nhân cách."* Địa vị xã hội được quyết định nghiêm ngặt bởi số lượng cạnh và độ đều của các góc. | Các thực thể kế thừa đẳng cấp hình học chính xác dựa trên số đỉnh (đa giác N cạnh) và tính đều đặn. |
| **Phụ nữ (Đoạn thẳng)** | Là những đường thẳng không có bề dày góc. Vì gần như vô hình khi nhìn trực diện và sắc bén như dao cạo, họ buộc phải liên tục cất tiếng kêu hòa bình và đi cửa riêng. | Thể hiện dưới dạng đoạn thẳng 1D (`shape: 'line'`). Nhanh nhẹn vượt trội, cách di chuyển và cơ chế trú ẩn đặc thù. |
| **Binh lính & Thợ thuyền** | Tam giác cân với góc đỉnh rất hẹp và nhọn hoắt (nguy hiểm, dễ kích động, mầm mống bạo loạn). | **Binh lính (Soldier)** (`#ff7b72`): Chiến binh sắc bén với lực công kích cao, kỷ luật quân sự và tuần tra bảo vệ biên giới. |
| **Thợ thủ công & Trung lưu** | Tam giác đều (3 cạnh bằng nhau) — tầng lớp lao động ổn định và đáng kính. | **Thợ thủ công (Artisans)** (3–4 cạnh, `#f2cc60`): Nông dân, người hái lượm và thợ xây phụ trách thu hoạch và bảo dưỡng nhà cửa. |
| **Thân sĩ & Trí thức** | Hình vuông (4 cạnh) và Ngũ giác (5 cạnh) — tầng lớp quản lý và chuyên gia thượng lưu. | **Thân sĩ** (4 cạnh, `#ffa657`) & **Chuyên gia** (5 cạnh, `#d2a8ff`): Đảm nhiệm các vai trò quản trị và chuyên trách. |
| **Giới Quý tộc** | Lục giác (6 cạnh) và các đa giác cao hơn — tầng lớp quý tộc và lãnh đạo nhà nước. | **Quý tộc** (6–8 cạnh, `#79c0ff`): Có tầm ảnh hưởng xã hội lớn và được ưu tiên trong gia phả dòng tộc. |
| **Hàng Giáo phẩm (Hình tròn)** | Đa giác có quá nhiều cạnh (≥ 24 đến hàng trăm) đến mức các đỉnh không còn nhận thấy được, tạo thành vòng tròn trơn nhẵn. Nắm giữ luật pháp và tôn giáo. | **Giáo sĩ (Priest)** (≥ 24 cạnh, `#e6edf3`): Phát hào quang xoa dịu, chữa lành vết thương/bệnh tật cho đồng loại và kháng dịch bệnh. |

---

## 2. "Định luật Tự nhiên" & Sự Thăng tiến Thế hệ

- **Trong Tiểu thuyết**:
  - Abbott xây dựng **"Định luật Phát triển Hướng thượng"**: Một bé trai con của đa giác đều hầu như luôn thừa hưởng **nhiều hơn cha mình một cạnh** (ví dụ: Hình Vuông sinh ra Ngũ Giác, rồi sinh ra Lục Giác), nâng tầm dòng dõi hướng tới sự hoàn hảo của Hình Tròn qua nhiều thế hệ.
  - Những kẻ **"Dị dạng"** (các cạnh/góc bất thường) bị coi là mối nguy hiểm cho xã hội và bị giam giữ hoặc xử tử.
- **Trong Ứng dụng Mô phỏng**:
  - **Tiến hóa thế hệ**: Thế hệ con kế thừa các đặc tính từ cha mẹ với xác suất tăng cạnh (`sides += 1`), mô phỏng chân thực sự thăng tiến dần dần qua các thời kỳ lịch sử.
  - **Dị tật & Giáng cấp**: Sinh vật phát triển dị tật gen hoặc gặp chấn thương sẽ bị theo dõi chỉ số bất thường, bị cộng đồng đánh giá và có dấu hiệu nhận biết trực quan riêng.
  - **Gia phả dòng họ**: Cây phả hệ lưu giữ chi tiết cha, mẹ và dòng dõi qua hàng thập kỷ trong lịch sử thế giới.

---

## 3. Nhận biết Thị giác, Khí quyển & Sương mù

- **Trong Tiểu thuyết**:
  - Trong thế giới 2 chiều phẳng, mọi cư dân nhìn từ cạnh bên đều chỉ là một đoạn thẳng!
  - Ở **Vùng Nam Sương mù**, cư dân sử dụng **"Nhận biết bằng mắt"** — phán đoán góc và khoảng cách của một đa giác đang đến gần qua tốc độ mờ dần của các cạnh trong sương mù khí quyển.
  - Ở **Vùng Bắc Trong trẻo**, họ phải dựa vào **"Sờ soạng"** (chạm vào các đỉnh bằng đầu ngón tay).
- **Trong Ứng dụng Mô phỏng**:
  - **Động cơ thời tiết động**: Mô phỏng 4 trạng thái **Quang đãng**, **Sương mù**, **Mưa** và **Bão tố**.
  - **Tầm nhìn khí quyển**: Sương mù và bão tố trực tiếp thu hẹp bán kính quan sát của sinh vật, buộc chúng phải dùng tín hiệu âm thanh và cảm biến khoảng cách gần.
  - **Ngày & Đêm**: Đường cong chiếu sáng thay đổi tự nhiên qua bình minh, giữa trưa, hoàng hôn và đêm tối mịt mù, thúc đẩy sinh vật tìm đường về nơi trú ẩn.

---

## 4. Nhà ở, Khu định cư & Kiến trúc Lãnh thổ

- **Trong Tiểu thuyết**:
  - Nhà ở bắt buộc phải có hình ngũ giác hoặc lục giác với các lối vào phân biệt: cửa nhỏ phía sau cho phụ nữ (đoạn thẳng) và cửa chính cho nam giới đa giác.
- **Trong Ứng dụng Mô phỏng**:
  - **Kinh tế định cư**: Nhà cửa là các cấu trúc vật lý 2D thực thụ với ranh giới bên trong, cửa ra vào có hướng (`bắc`, `đông`, `nam`, `tây`) và số giường ngủ giới hạn.
  - **Trụ sở duy nhất**: Mỗi bộ tộc sở hữu đúng **một Nhà Trụ sở / Đại bản doanh** (nơi ở của Thủ lĩnh) cùng các chòi trú ẩn vệ tinh xung quanh.
  - **Nhu cầu trú ẩn**: Sinh vật tìm về nhà để ngủ khi màn đêm buông xuống, tránh sương muối mùa đông, hồi phục thể lực và nuôi dạy con cái.
  - **Điều hướng qua cửa**: Sinh vật tính toán điểm đứng chờ thông minh để di chuyển mượt mà qua cửa khi trời tối và tỏa ra tìm thức ăn khi bình minh, không bị kẹt vào tường.

---

## 5. Ngoại giao Bộ tộc, Linh thú Totem & Xã hội Tự trị

Khác với chính quyền tập quyền thời Victoria trong sách, ứng dụng triển khai **mô phỏng xã hội tiến hóa**:
- **Linh thú Totem**: Các bộ tộc tôn thờ linh thú riêng (🐺 Sói, 🐻 Gấu, 🦅 Đại bàng, 🦌 Hươu, 🐍 Rắn, 🦉 Cú), tạo nên xu hướng tính cách và sự chuyên môn hóa kinh tế khác biệt giữa các chiến binh, nông dân và thợ săn.
- **Ngoại giao, Cống nạp & Chiến tranh**: Quan hệ bộ tộc diễn tiến linh hoạt với các hiệp ước hòa bình, liên minh quân sự, nộp cống và nguy cơ phân liệt phe phái.
- **Quyền tự trị cá nhân**: Các hình mẫu tính cách độc lập (Dũng cảm, Cẩn trọng, Vị tha, Tham lam, Thám hiểm, Thợ xây) mang giỏ thức ăn cá nhân, vũ khí và phản xạ tự cứu mình khi nguy cấp.

---

## 6. Chiều Không Gian Cao Hơn: Người Dùng Chính Là "The Sphere"

Mối liên kết sâu sắc nhất giữa ứng dụng và tác phẩm chính là **vai trò của người dùng**:
- Trong tiểu thuyết, nhân vật chính **A Square (Hình Vuông)** được viếng thăm bởi **A Sphere (Khối Cầu)** đến từ *Spaceland (Không Gian 3D)*, người có thể nhìn từ trục Z xuống, thấy được bên trong các căn phòng khóa kín, nhìn thấu nội tạng và thao túng mặt phẳng 2D như một Thượng đế toàn năng.
- **Trong Ứng dụng của chúng ta**:
  - **Bạn chính là Khối Cầu (Thượng đế)**: Khi nhìn vào màn hình, bạn đang quan sát Xứ Phẳng từ chiều không gian thứ ba.
  - **Bảng The Sphere**: Bạn nắm giữ quyền năng tối thượng để thay đổi "Định luật của Tự nhiên" theo thời gian thực — kích hoạt nạn đói, điều chỉnh sinh trưởng thức ăn, phát tán hoặc chữa lành bệnh tật, tạo ra mùa đông băng giá hoặc ban phước lành thịnh vượng cho các bộ tộc.
""",
    "fr": r"""
# Flatland : Le Roman vs. La Simulation

Étude comparative entre le classique satirique d'**Edwin A. Abbott (1884), *Flatland: A Romance of Many Dimensions*** et cette simulation autonome de vie artificielle.

---

## 1. Castes, Géométrie & Hiérarchie Sociale

| Dimension | Livre d'Abbott (*Flatland*, 1884) | Notre Simulation (*Flatland Simulator*) |
| :--- | :--- | :--- |
| **Principe hiérarchique** | *"La configuration fait l'homme."* Le rang social est strictement déterminé par le nombre de côtés et la régularité des angles. | Les entités héritent de castes géométriques précises basées sur leur nombre de sommets (N-gones) et leur régularité. |
| **Femmes (Lignes)** | Lignes droites sans épaisseur angulaire. Invisibles de face et acérées comme des lames, elles doivent émettre un cri de paix continu et emprunter des portes dédiées. | Représentées comme des segments 1D (`shape: 'line'`). Remarquablement agiles, avec une dynamique de déplacement et d'abri spécifique. |
| **Ouvriers / Soldats** | Triangles isocèles aux angles sommitaux étroits et tranchants (dangereux, instables, enclins aux révoltes). | **Soldats** (`#ff7b72`) : Combattants aux attaques perçantes, discipline martiale et patrouilles défensives aux frontières. |
| **Artisans & Classe moyenne** | Triangles équilatéraux (3 côtés égaux) — marchands et travailleurs respectables et stables. | **Artisans** (3–4 côtés, `#f2cc60`) : Fermiers, cueilleurs et bâtisseurs chargés des récoltes et de l'entretien des demeures. |
| **Gentlemen & Professionnels** | Carrés (4 côtés) et Pentagones (5 côtés) — classes administratives et bourgeoises dirigeantes. | **Gentlemen** (4 côtés, `#ffa657`) et **Professionnels** (5 côtés, `#d2a8ff`) : Rôles d'administration et de gestion spécialisée. |
| **Noblesse** | Hexagones (6 côtés) et polygones supérieurs — aristocrates et hommes d'État influents. | **Nobles** (6–8 côtés, `#79c0ff`) : Haute influence et priorité dans la pérennité de la lignée. |
| **Clergé (Cercles)** | Polygones aux sommets si innombrables (≥ 24 à plusieurs centaines) qu'ils forment des cercles parfaits. Dirigent religion et morale. | **Prêtres** (≥ 24 côtés, `#e6edf3`) : Émettent une aura apaisante, soignent leurs alliés et résistent naturellement aux épidémies. |

---

## 2. La "Loi de la Nature" & L'Ascension Générationnelle

- **Dans le Livre** :
  - Abbott pose la **"Loi du Progrès Ascendant"** : Le fils d'un polygone régulier gagne presque toujours **un côté de plus** que son père (un Carré engendre un Pentagone, dont le fils sera Hexagone), élevant la lignée vers la perfection circulaire.
  - Les rares **"Irréguliers"** (aux angles asymétriques) sont perçus comme une menace publique et enfermés ou éliminés.
- **Dans l'Application** :
  - **Évolution générationnelle** : La progéniture hérite des traits ancestraux avec une probabilité d'accroissement (`sides += 1`), illustrant l'ascension historique vers le cercle.
  - **Irrégularité & Déclassement** : Les entités développant des mutations asymétriques voient leur anomalie mesurée et signalée visuellement.
  - **Généalogie dynastique** : L'arbre généalogique retrace pères, mères et filiations sur des décennies d'histoire du monde.

---

## 3. Reconnaissance Visuelle, Météo & Perception

- **Dans le Livre** :
  - Dans un monde 2D, tous les habitants ressemblent vus de profil à de simples lignes !
  - Dans le **Sud Brumeux**, les Flatlandais pratiquent la **"Reconnaissance Visuelle"** — estimant l'angle et la distance d'un polygone selon la rapidité avec laquelle ses bords se fondent dans le brouillard.
  - Dans le **Nord Clair**, ils doivent recourir au **"Palper"** (toucher les sommets du bout des doigts).
- **Dans l'Application** :
  - **Moteur météo dynamique** : Alterne entre **Ciel dégagé**, **Brouillard**, **Pluie** et **Tempête**.
  - **Vision atmosphérique** : La brume et les orages réduisent drastiquement le champ visuel des créatures, les obligeant à se fier aux alarmes acoustiques de proximité.
  - **Cycle Jour/Nuit** : La luminosité varie de l'aube au crépuscule jusqu'à l'obscurité totale, guidant les créatures vers la sécurité de leurs foyers.

---

## 4. Habitats, Colonies & Architecture Territoriale

- **Dans le Livre** :
  - Les maisons sont obligatoirement pentagonales ou hexagonales, avec des entrées distinctes pour les femmes et les hommes.
- **Dans l'Application** :
  - **Économie coloniale** : Les maisons sont des bâtisses 2D concrètes avec portes orientées (`nord`, `est`, `sud`, `ouest`) et nombre de lits limité.
  - **Demeure Principale Unique** : Chaque clan fonde exactement **une Demeure Principale / QG** (siège du chef) entourée d'abris secondaires.
  - **Fonction du refuge** : Les créatures y dorment la nuit, s'y protègent des gelées d'hiver, s'y soignent et y éduquent leurs petits.
  - **Navigation de franchissement** : Les créatures calculent des points de passage fluides pour franchir les seuils sans rester bloquées contre les parois.

---

## 5. Diplomatie de Clan, Totems & Société Évolutive

Au-delà de l'État victorien centralisé d'Abbott, l'application met en scène une **société évolutive vivante** :
- **Totems & Spécialisation** : Vénération de totems animaux (🐺 Loup, 🐻 Ours, 🦅 Aigle, 🦌 Cerf, 🐍 Serpent, 🦉 Chouette), orientant les vocations du clan.
- **Diplomatie, Tributs & Conflits** : Relations mouvantes entre clans incluant traités, guerres de conquête, pillages de greniers et scissions.
- **Autonomie individuelle** : Tempéraments personnalisés (Brave, Prudent, Altruiste, Avare, Explorateur, Bâtisseur) dotés de paniers individuels et d'outils façonnés.

---

## 6. La Dimension Supérieure : L'Utilisateur est "La Sphère"

Le lien le plus fondamental entre le livre et l'application réside dans le **statut de l'utilisateur** :
- Dans *Flatland*, le protagoniste **A Square** reçoit la visite d'une **Sphère** venue de *Spaceland*, capable de contempler le monde depuis l'axe vertical, de voir à travers les portes closes et de modifier l'univers 2D avec une toute-puissance céleste.
- **Dans notre Application** :
  - **Vous êtes La Sphère (Dieu)** : Devant votre écran, vous observez Flatland depuis la troisième dimension.
  - **Le Panneau de La Sphère** : Vous détenez le pouvoir de réécrire les "Lois de la Nature" en direct — déclencher des famines, moduler la fertilité, éradiquer ou propager les fléaux et guider les clans vers la gloire.
""",
}


# ---------------------------------------------------------------------
# GodLaws Hints Translations (72 parameters)
# ---------------------------------------------------------------------
LAW_HINTS_I18N = {
    "en": {
        "boundary": "World border topology: wrap (seamless toroidal loop) vs clamp (solid collision walls).",
        "food_count": "Living food plants maintained across the world (summer ×1.2, winter ×0.5).",
        "energy_max": "Maximum metabolic energy capacity an organism can store (10–500).",
        "energy_decay_per_tick": "Baseline metabolic burn rate per tick without food (0.025).",
        "energy_from_food": "Base energy yield from harvesting a mature plant (berry 48, grass 32, mushroom 24, poison 8).",
        "plant_variants_enabled": "Master switch enabling botanical biodiversity across 6 distinct functional plant species.",
        "plant_growth_rate": "How fast sprouted plants mature into harvestable food (0.045).",
        "plant_spread_rate": "Probability per tick that a mature plant drops seeds into adjacent fertile ground (0.006).",
        "nutrient_cycle_rate": "Acceleration of plant growth near decomposing corpses (0.65) — death nourishes new life.",
        "poison_rate": "Probability a new wild sprout is poisonous (-30 HP damage on ingestion).",
        "food_decay_enabled": "Enables mature plants to naturally wither over time and fertilize the living soil.",
        "food_lifespan_ticks": "Ticks a mature plant lives before naturally withering into the living soil grid (8000).",
        "agriculture_enabled": "Enables seed gathering, cultivated farm plots (2× growth, 2.5× yield), irrigation furrows, and tending.",
        "granaries_enabled": "Enables communal settlement granaries to stockpile grain and berries against winter.",
        "granary_capacity": "Units of food a settlement granary can store (400) — feasts fire at ≥80% capacity.",
        "perceive_radius": "Base perception sight radius (16) — scaled by caste (Woman 0.8×, Priest 1.35×), night (0.6×), and fog (0.6×).",
        "eat_radius": "Physical contact distance required to consume a plant, corpse, or prey item (1.4).",
        "hungry_ratio": "Energy threshold (≤35%) feeding normalized energy into neural network input slot 0 to trigger foraging.",
        "starving_ratio": "Severe energy threshold (≤15%) triggering desperation sprint and pulsing survival distress.",
        "steer_turn": "Maximum heading angular turn agility per tick, scaled by creature moment of inertia Izz.",
        "birth_enabled": "Master switch enabling reproduction, mating, and generational ascendance.",
        "lifespan_mult": "Multiplier scaling all caste lifespans (Woman: 4,800 ticks → Priest: 9,000 ticks).",
        "adult_age": "Ticks required for an infant/juvenile to mature into a sexually fertile adult (220).",
        "birth_rate": "Base reproduction probability per eligible adult mating pair per tick (0.28).",
        "carrying_capacity": "Population density threshold above which fertility gradually fades (-1 = auto).",
        "max_population": "Hard global population cap preventing any new births until density declines (-1 = auto).",
        "mutation_rate": "Probability a newborn son deviates ±1 side from classical caste inheritance (0.05).",
        "sex_ratio": "Probability a newborn child is a son (ascending polygon) vs daughter (agile line) (0.50).",
        "max_sides": "Upper limit on regular polygon vertex ascendance (up to Priest / Circle status) (24).",
        "euthanasia_threshold": "Irregularity threshold; deformed infants exceeding this are consumed at adulthood (0.70).",
        "mutation_sigma": "Gaussian mutation standard deviation (σ) applied to genome weights during crossover (0.08).",
        "crossover_rate": "Probability of uniform 50/50 parental genome blending during sexual reproduction (0.50).",
        "morphology_annealing_enabled": "Master switch for geometric physics — polar (r,φ) annealing, SAT polygon collision, and trait baking.",
        "annealing_decay_generations": "Generations over which polar morphology annealing decays from Abbott templates to free evolution (150).",
        "disease_enabled": "Master switch for infectious pathogen outbreaks and contagion transmission.",
        "disease_outbreak_rate": "Spontaneous plague outbreak probability per tick during crowded conditions (0.00006).",
        "disease_rate": "Contagion transmission probability per tick within contact range (0.035).",
        "disease_energy_drain": "Metabolic energy drained per tick from actively infected creatures (0.05).",
        "disease_lethality": "Direct health (HP) damage dealt per tick to actively diseased creatures (0.18).",
        "weather_enabled": "Master switch for dynamic meteorological cycles (sun, rain, fog, storms).",
        "sleep_enabled": "Enables diurnal sleep cycles, house resting, and oral lore transfer after dark.",
        "day_length": "Total duration in ticks of a single diurnal day/night cycle (1200).",
        "season_length": "Duration in ticks of each season (Spring, Summer, Autumn, Winter) (12000).",
        "winter_food_mult": "Winter seasonal food abundance multiplier (0.70 gentle, 0.50 harsh, 0.30 extinction).",
        "night_sight_mult": "Perception radius multiplier during night ticks for non-nocturnal castes (0.60).",
        "weather_change_rate": "Frequency of meteorological transitions between clear, rain, fog, and storm (0.002).",
        "weather_sickness_enabled": "Enables exposure chill and hypothermia when caught unsheltered in wet or freezing weather.",
        "chill_drain": "Direct health drain per tick when chilled outdoors without shelter (0.18).",
        "shelter_enabled": "Master switch for house claiming, door navigation, and roof protection.",
        "exposure_drain": "Health and energy drain per tick when outdoors during harsh weather (0.025).",
        "house_capacity": "Bed capacity inside a settlement hall (12); excess members sleep outdoors.",
        "house_decay_ticks": "Ticks before an abandoned, roofless house crumbles into ruins (10000).",
        "rest_recovery_mult": "Health regeneration multiplier when sleeping indoors under a roof (2.0).",
        "territory_enabled": "Enables clan boundary markings, territory defence, and trespass penalties.",
        "territory_radius": "Radius of clan territorial influence around settlement houses (16).",
        "trespass_decay": "Diplomatic relation points lost per tick when a rival clan enters marked territory (0.15).",
        "max_clans": "Maximum number of sovereign clans spawned during world initialization (-1 = auto).",
        "totems_enabled": "Enables Sacred Avatar totem blessings for each clan settlement.",
        "succession_enabled": "Enables dynamic governance leadership transfers on chieftain death.",
        "communication_enabled": "Enables vocalizations, alarm chirps, peace hums, and emotional thought bubbles.",
        "knowledge_enabled": "Enables spatial memory, waypoint mapping, and rumor broadcasting among kin.",
        "schism_enabled": "Enables internal clan fractures when members starve or lack shelter.",
        "schism_threshold": "Dissatisfaction fraction (hunger, homelessness) triggering a factional clan schism (0.40).",
        "war_enabled": "Enables inter-clan warfare, tactical raids, and territorial conquest.",
        "attack_damage": "Base damage dealt by soldiers and warriors in inter-clan battles (32.0).",
        "predation_enabled": "Enables carnivorous predator-prey ecology and hunting dynamics.",
        "predator_ratio": "Fraction of population spawned as predatory carnivores hunting prey (0.02).",
        "hunt_radius": "Aggro detection radius within which carnivores and war parties acquire targets (16.0).",
        "bite_damage": "Combat damage dealt per carnivore attack or predatory strike (28.0).",
        "energy_from_prey": "Caloric energy extracted from slaying and eating a prey creature (45.0).",
        "fear_radius": "Distance at which herbivores and vulnerable castes detect threats and execute evasion (12.0).",
        "coalitions_enabled": "Enables mutual defensive alliances and diplomatic treaties between friendly clans.",
        "coalition_threshold": "Diplomatic trust score required for two friendly clans to form a defensive coalition (40).",
        "leader_decisions_enabled": "Enables chieftain governance bylaws (rationing, martial law, war declarations).",
        "resource_sharing_enabled": "Enables communal settlement larders and altruistic basket food sharing.",
        "larder_capacity": "Energy capacity of settlement communal food stores where surplus is shared (300).",
        "cannibalism_enabled": "Enables desperate consumption of the living during extreme starvation.",
        "eat_kin_enabled": "Allows consumption of deceased or weak clanmates at the cost of tribal exile and feuds.",
        "cannibalism_energy": "Energy gained by starving creatures resorting to eating fallen kin or rivals (45.0).",
        "theology_enabled": "Enables the 8 Sacred Avatars, shrines, temples, miracles, and divine tithes.",
        "tithe_rate": "Fraction of energy devout worshippers offer at shrines each dawn & dusk to build clan faith (0.04).",
        "temple_faith_cost": "Faith points required to consecrate a glowing Temple of the Sphere (400.0).",
        "age_enabled": "Enables historical epoch progression (Golden Age, Ice Age, Age of Chaos, Age of Plague).",
        "age_length": "Duration in ticks per world historical epoch (50000).",
        "culture_enabled": "Enables traditions, governance archetypes, and cultural diffusion.",
        "culture_spread_rate": "Rate at which allied clans sharing borders adopt common cultural traits and beliefs (0.0005).",
        "rivers_enabled": "Enables water channels, fords, water currents, bridges, and dams.",
        "river_count": "Number of procedural river channels carved across the terrain at world generation (2).",
        "relief_enabled": "Enables topographical elevation, slope inertia, cliffs, and road packing.",
        "structural_enabled": "Enables weather wear on buildings, builder repairs, and roof collapse into rubble.",
        "earthquake_enabled": "Enables seismic tremors that shake terrain and damage weakened structures.",
        "earthquake_rate": "Frequency of seismic quakes that crack buildings and shake terrain (0.00008).",
        "lightning_enabled": "Enables real lightning strikes during storms that ignite fires and damage creatures.",
        "lightning_strike_rate": "Frequency of deadly electrical arc strikes during thunder storms (0.0015).",
        "wildfire_enabled": "Enables combustive flame propagation across dense vegetation and forests.",
        "fire_rate": "Probability per tick that a mature plant ignites during dry spells or lightning strikes (0.00008).",
        "disaster_enabled": "Enables cataclysmic meteors, floods, and natural world disturbances.",
        "disaster_rate": "Stochastic probability of catastrophic environmental disasters (0.0003).",
        "anomaly_count": "Number of mysterious spatial anomaly zones altering local physics (3).",
        "door_clearance": "Width multiplier for house doorways relative to the largest creature size (1.5).",
    },
    "vi": {
        "boundary": "Địa hình đường biên thế giới: 'wrap' (vòng lặp xuyến liền mạch) vs 'clamp' (tường va chạm cứng).",
        "food_count": "Số lượng cây thức ăn sống được duy trì trên toàn thế giới (mùa hè ×1.2, mùa đông ×0.5).",
        "energy_max": "Mức năng lượng trao đổi chất tối đa một sinh vật có thể tích trữ (10–500).",
        "energy_decay_per_tick": "Mức tiêu hao năng lượng cơ bản mỗi tick khi không có thức ăn (0.025).",
        "energy_from_food": "Năng lượng thu được khi thu hoạch cây chín (quả mọng 48, cỏ 32, nấm 24, độc thảo 8).",
        "plant_variants_enabled": "Công tắc chính kích hoạt đa dạng sinh học với 6 loài thực vật chức năng.",
        "plant_growth_rate": "Tốc độ cây mầm lớn lên thành thức ăn có thể thu hoạch (0.045).",
        "plant_spread_rate": "Xác suất mỗi tick cây chín rụng hạt xuống vùng đất màu mỡ xung quanh (0.006).",
        "nutrient_cycle_rate": "Tốc độ gia tăng sinh trưởng thực vật quanh xác sinh vật phân hủy (0.65) — cái chết nuôi dưỡng sự sống mới.",
        "poison_rate": "Xác suất một mầm cây mới mọc mang độc tính (-30 HP sát thương khi ăn phải).",
        "food_decay_enabled": "Cho phép cây chín tự nhiên tàn lụi theo thời gian và bồi đắp chất dinh dưỡng cho đất.",
        "food_lifespan_ticks": "Thời gian tính bằng tick một cây chín tồn tại trước khi tàn lụi vào đất (8000).",
        "agriculture_enabled": "Kích hoạt thu nhặt hạt giống, luống canh tác (lớn nhanh 2×, sản lượng 2.5×), rãnh tưới và làm cỏ.",
        "granaries_enabled": "Kích hoạt kho thóc cộng đồng của khu định cư để tích trữ ngũ cốc và quả mọng qua mùa đông.",
        "granary_capacity": "Dung lượng thức ăn kho thóc có thể chứa (400) — yến tiệc kích hoạt khi đạt ≥80% dung lượng.",
        "perceive_radius": "Bán kính thị giác cơ bản (16) — điều chỉnh theo giai cấp (Nữ giới 0.8×, Giáo sĩ 1.35×), đêm (0.6×) và sương mù (0.6×).",
        "eat_radius": "Khoảng cách tiếp xúc vật lý tối đa để ăn cây, xác chết hoặc con mồi (1.4).",
        "hungry_ratio": "Ngưỡng năng lượng đói (≤35%) đưa tín hiệu vào mạng nơ-ron để kích hoạt hành vi tìm thức ăn.",
        "starving_ratio": "Ngưỡng kiệt sức nghiêm trọng (≤15%) kích hoạt nước rút sinh tồn và phát tín hiệu cầu cứu.",
        "steer_turn": "Góc quay đầu tối đa mỗi tick, tỷ lệ theo mô-men quán tính Izz của sinh vật.",
        "birth_enabled": "Công tắc chính cho phép sinh sản, giao phối và thăng tiến thế hệ.",
        "lifespan_mult": "Hệ số nhân tuổi thọ cho tất cả giai cấp (Nữ giới: 4.800 ticks → Giáo sĩ: 9.000 ticks).",
        "adult_age": "Số tick để ấu trùng trưởng thành thành cá thể có khả năng sinh sản (220).",
        "birth_rate": "Xác suất sinh sản cơ bản cho mỗi cặp giao phối đủ điều kiện mỗi tick (0.28).",
        "carrying_capacity": "Ngưỡng mật độ dân số mà khi vượt qua, khả năng sinh sản sẽ giảm dần (-1 = tự động).",
        "max_population": "Giới hạn dân số toàn cầu tuyệt đối, chặn mọi ca sinh mới cho đến khi mật độ giảm (-1 = tự động).",
        "mutation_rate": "Xác suất con trai sinh ra lệch ±1 cạnh so với kế thừa giai cấp cổ điển (0.05).",
        "sex_ratio": "Xác suất một đứa trẻ sinh ra là con trai (đa giác thăng tiến) vs con gái (đoạn thẳng nhanh nhẹn) (0.50).",
        "max_sides": "Giới hạn số cạnh tối đa của đa giác đều (lên đến cấp Giáo sĩ / Hình tròn) (24).",
        "euthanasia_threshold": "Ngưỡng dị tật hình thể; ấu trùng vượt quá mức này sẽ bị tiêu hủy khi trưởng thành (0.70).",
        "mutation_sigma": "Độ lệch chuẩn đột biến Gauss (σ) áp dụng lên trọng số bộ gen khi lai ghép (0.08).",
        "crossover_rate": "Tỷ lệ hòa trộn 50/50 bộ gen cha mẹ trong quá trình sinh sản hữu tính (0.50).",
        "morphology_annealing_enabled": "Công tắc chính cho vật lý hình học — ủ nhiệt (r,φ), va chạm đa giác SAT và tính toán đặc tính thể chất.",
        "annealing_decay_generations": "Số thế hệ để quá trình ủ nhiệt hình thái chuyển dần từ mẫu chuẩn Abbott sang tiến hóa tự do (150).",
        "disease_enabled": "Công tắc chính cho bùng phát mầm bệnh truyền nhiễm và lây lan dịch tả.",
        "disease_outbreak_rate": "Xác suất bùng phát dịch bệnh tự phát mỗi tick trong điều kiện đông đúc (0.00006).",
        "disease_rate": "Xác suất lây truyền bệnh mỗi tick trong cự ly tiếp xúc gần (0.035).",
        "disease_energy_drain": "Năng lượng trao đổi chất bị rút cạn mỗi tick ở sinh vật đang nhiễm bệnh (0.05).",
        "disease_lethality": "Sát thương máu (HP) trực tiếp trừ mỗi tick lên sinh vật mắc bệnh (0.18).",
        "weather_enabled": "Công tắc chính cho chu kỳ khí tượng động (nắng, mưa, sương mù, bão tố).",
        "sleep_enabled": "Kích hoạt chu kỳ ngủ ngày/đêm, nghỉ ngơi trong nhà và truyền khẩu tri thức sau khi trời tối.",
        "day_length": "Tổng độ dài tính bằng tick của một chu kỳ ngày/đêm (1200).",
        "season_length": "Độ dài tính bằng tick của mỗi mùa (Xuân, Hạ, Thu, Đông) (12000).",
        "winter_food_mult": "Hệ số thức ăn theo mùa vào mùa đông (0.70 êm dịu, 0.50 khắc nghiệt, 0.30 tuyệt chủng).",
        "night_sight_mult": "Hệ số tầm nhìn ban đêm đối với các loài sinh hoạt ban ngày (0.60).",
        "weather_change_rate": "Tần suất chuyển đổi trạng thái khí tượng giữa trời trong, mưa, sương mù và bão (0.002).",
        "weather_sickness_enabled": "Kích hoạt hạ thân nhiệt và cảm lạnh khi ở ngoài trời không có mái che lúc mưa rét.",
        "chill_drain": "Sát thương máu trực tiếp mỗi tick khi bị nhiễm lạnh ngoài trời không có nơi trú ẩn (0.18).",
        "shelter_enabled": "Công tắc chính cho cơ chế chiếm nhà, điều hướng qua cửa và mái che bảo vệ.",
        "exposure_drain": "Hao tổn máu và năng lượng mỗi tick khi ở ngoài trời lúc thời tiết khắc nghiệt (0.025).",
        "house_capacity": "Sức chứa giường ngủ trong một sảnh nhà định cư (12); thành viên dôi dư phải ngủ ngoài trời.",
        "house_decay_ticks": "Số tick trước khi một căn nhà bỏ hoang, mất mái sụp đổ thành đống đổ nát (10000).",
        "rest_recovery_mult": "Hệ số hồi phục sinh lực khi ngủ trong nhà có mái che (2.0).",
        "territory_enabled": "Kích hoạt cắm mốc ranh giới bộ tộc, bảo vệ lãnh thổ và phạt xâm phạm.",
        "territory_radius": "Bán kính tầm ảnh hưởng lãnh thổ của bộ tộc xung quanh các căn nhà (16).",
        "trespass_decay": "Điểm quan hệ ngoại giao mất đi mỗi tick khi bộ tộc đối địch xâm phạm lãnh thổ (0.15).",
        "max_clans": "Số lượng bộ tộc tối đa được khởi tạo khi lập thế giới mới (-1 = tự động).",
        "totems_enabled": "Kích hoạt phước lành từ Linh thú Totem Hóa thân cho mỗi khu định cư bộ tộc.",
        "succession_enabled": "Kích hoạt cơ chế kế vị lãnh đạo bộ tộc linh hoạt khi thủ lĩnh qua đời.",
        "communication_enabled": "Kích hoạt phát âm, tiếng chim báo động, tiếng ngân hòa bình và bong bóng suy nghĩ cảm xúc.",
        "knowledge_enabled": "Kích hoạt bộ nhớ không gian, bản đồ lộ trình và truyền tin đồn trong bộ tộc.",
        "schism_enabled": "Kích hoạt phân liệt bộ tộc khi thành viên bị đói hoặc thiếu chỗ ở.",
        "schism_threshold": "Tỷ lệ bất mãn (đói khát, vô gia cư) kích hoạt cuộc phân liệt phe phái nội bộ (0.40).",
        "war_enabled": "Kích hoạt chiến tranh liên bộ tộc, tập kích chiến thuật và xâm chiếm lãnh thổ.",
        "attack_damage": "Sát thương cơ bản do binh lính và chiến binh gây ra trong giao tranh (32.0).",
        "predation_enabled": "Kích hoạt sinh thái thú săn mồi ăn thịt và con mồi ăn cỏ.",
        "predator_ratio": "Tỷ lệ dân số sinh ra là loài thú săn mồi chuyên ăn thịt (0.02).",
        "hunt_radius": "Bán kính phát hiện con mồi mà thú săn mồi hoặc đội săn nhắm tới (16.0).",
        "bite_damage": "Sát thương chiến đấu gây ra trong mỗi cú cắn hoặc vồ của thú săn mồi (28.0).",
        "energy_from_prey": "Năng lượng calo hấp thụ được khi hạ gục và ăn thịt con mồi (45.0).",
        "fear_radius": "Khoảng cách mà loài ăn cỏ và giai cấp dễ tổn thương phát hiện nguy hiểm để bỏ chạy (12.0).",
        "coalitions_enabled": "Kích hoạt liên minh phòng thủ tương trợ và hiệp ước ngoại giao giữa các bộ tộc thân thiện.",
        "coalition_threshold": "Điểm tin cậy ngoại giao cần thiết để hai bộ tộc thân hữu lập liên minh phòng thủ (40).",
        "leader_decisions_enabled": "Kích hoạt các sắc lệnh quản trị của tù trưởng (chia khẩu phần, thiết quân luật, tuyên chiến).",
        "resource_sharing_enabled": "Kích hoạt kho lương chung của khu định cư và chia sẻ thức ăn từ giỏ cá nhân.",
        "larder_capacity": "Dung lượng dự trữ năng lượng của kho lương thực chung trong khu định cư (300).",
        "cannibalism_enabled": "Kích hoạt hành vi ăn thịt đồng loại trong tuyệt vọng khi nạn đói cùng cực xảy ra.",
        "eat_kin_enabled": "Cho phép ăn thịt đồng loại đã chết với cái giá là bị trục xuất khỏi bộ tộc và gây thù hằn.",
        "cannibalism_energy": "Năng lượng hấp thụ được khi sinh vật chết đói ăn thịt đồng loại hoặc kẻ thù (45.0).",
        "theology_enabled": "Kích hoạt 8 Linh thú Hóa thân, điện thờ, đền đài, phép màu và dâng nộp đức tin.",
        "tithe_rate": "Tỷ lệ năng lượng tín đồ sùng đạo dâng nộp tại điện thờ mỗi bình minh & hoàng hôn để tích lũy đức tin (0.04).",
        "temple_faith_cost": "Điểm đức tin cần thiết để thánh hóa một Ngôi Đền Khối Cầu rực sáng (400.0).",
        "age_enabled": "Kích hoạt tiến trình các kỷ nguyên lịch sử (Kỷ Hoàng kim, Kỷ Băng hà, Kỷ Hỗn mang, Kỷ Dịch bệnh).",
        "age_length": "Thời lượng tính bằng tick cho mỗi kỷ nguyên lịch sử thế giới (50000).",
        "culture_enabled": "Kích hoạt phong tục tập quán, thể chế quản trị và lan tỏa văn hóa.",
        "culture_spread_rate": "Tốc độ các bộ tộc láng giềng tiếp thu các nét văn hóa và tín ngưỡng của nhau (0.0005).",
        "rivers_enabled": "Kích hoạt dòng sông, khúc cạn, dòng chảy xiết, cầu cống và đập nước.",
        "river_count": "Số lượng kênh sông tự nhiên được kiến tạo trên địa hình khi lập thế giới (2).",
        "relief_enabled": "Kích hoạt độ cao địa hình, quán tính dốc, vách đá và đường mòn đầm nén.",
        "structural_enabled": "Kích hoạt sự hao mòn công trình do thời tiết, thợ xây sửa chữa và mái sập thành gạch vụn.",
        "earthquake_enabled": "Kích hoạt các chấn động địa chấn làm rung chuyển mặt đất và nứt vỡ nhà cửa.",
        "earthquake_rate": "Tần suất các trận động đất gây nứt vỡ công trình và sạt lở địa hình (0.00008).",
        "lightning_enabled": "Kích hoạt sét đánh chân thực trong bão, gây cháy rừng và sát thương sinh vật.",
        "lightning_strike_rate": "Tần suất các tia sét chết người giáng xuống trong cơn giông bão (0.0015).",
        "wildfire_enabled": "Kích hoạt sự bùng cháy và lan truyền ngọn lửa qua các thảm thực vật dày đặc.",
        "fire_rate": "Xác suất mỗi tick cây chín bốc cháy khi khô hạn hoặc sét đánh (0.00008).",
        "disaster_enabled": "Kích hoạt thiên thạch rơi, lũ quét và các thảm họa môi trường thảm khốc.",
        "disaster_rate": "Xác suất ngẫu nhiên xảy ra các thảm họa môi trường tàn khốc (0.0003).",
        "anomaly_count": "Số lượng dị thường không gian huyền bí làm biến dạng các quy luật vật lý cục bộ (3).",
        "door_clearance": "Hệ số độ rộng cửa nhà so với kích thước sinh vật lớn nhất (1.5).",
    },
    "fr": {
        "boundary": "Topologie des frontières : 'wrap' (boucle toroïdale continue) vs 'clamp' (parois rigides infranchissables).",
        "food_count": "Nombre de plantes nourricières maintenues dans le monde (été ×1.2, hiver ×0.5).",
        "energy_max": "Capacité métabolique maximale emmagasinable par un organisme (10–500).",
        "energy_decay_per_tick": "Taux de dépense métabolique de base par tick sans apport alimentaire (0.025).",
        "energy_from_food": "Énergie tirée de la récolte d'une plante mûre (baie 48, herbe 32, champignon 24, poison 8).",
        "plant_variants_enabled": "Interrupteur principal activant la biodiversité parmi 6 espèces végétales fonctionnelles.",
        "plant_growth_rate": "Vitesse de maturation des jeunes pousses en nourriture récoltable (0.045).",
        "plant_spread_rate": "Probabilité par tick qu'une plante mûre dissémine des graines sur un sol fertile adjacent (0.006).",
        "nutrient_cycle_rate": "Accélération de la pousse près des carcasses en décomposition (0.65) — la mort nourrit la vie.",
        "poison_rate": "Probabilité qu'une pousse sauvage soit toxique (-30 PV de dégâts en cas d'ingestion).",
        "food_decay_enabled": "Permet aux plantes mûres de flétrir naturellement et d'enrichir l'humus du sol.",
        "food_lifespan_ticks": "Durée de vie en ticks d'une plante mûre avant son retour à la terre (8000).",
        "agriculture_enabled": "Active la collecte de semences, parcelles labourées (croissance 2×, récolte 2.5×) et sarclage.",
        "granaries_enabled": "Permet aux colonies d'aménager des greniers collectifs pour stocker grains et baies.",
        "granary_capacity": "Capacité de stockage d'un grenier communal (400) — banquets à partir de ≥80% de remplissage.",
        "perceive_radius": "Rayon de vision de base (16) — modulé par caste (Femme 0.8×, Prêtre 1.35×), nuit (0.6×) et brume (0.6×).",
        "eat_radius": "Distance physique de contact requise pour ingérer une plante, dépouille ou proie (1.4).",
        "hungry_ratio": "Seuil de faim (≤35%) envoyant un signal au réseau neuronal pour déclencher la quête de vivres.",
        "starving_ratio": "Seuil de famine critique (≤15%) provoquant une course d'urgence et des appels de détresse.",
        "steer_turn": "Agilité angulaire maximale par tick, proportionnelle au moment d'inertie Izz.",
        "birth_enabled": "Interrupteur général commandant la reproduction, l'accouplement et l'ascendance de caste.",
        "lifespan_mult": "Multiplicateur de longévité pour toutes les castes (Femme : 4 800 ticks → Prêtre : 9 000 ticks).",
        "adult_age": "Ticks requis pour qu'un nouveau-né atteigne la maturité reproductrice (220).",
        "birth_rate": "Probabilité d'engendrement par couple adulte éligible et par tick (0.28).",
        "carrying_capacity": "Seuil de densité démographique au-delà duquel la fertilité faiblit progressivement (-1 = auto).",
        "max_population": "Plafond démographique absolu interdisant toute naissance tant que la densité reste trop forte (-1 = auto).",
        "mutation_rate": "Probabilité qu'un fils dévie de ±1 côté par rapport à la caste paternelle (0.05).",
        "sex_ratio": "Probabilité qu'un nouveau-né soit un fils (polygone ascendant) ou une fille (ligne agile) (0.50).",
        "max_sides": "Limite supérieure du nombre de côtés des polygones réguliers (jusqu'au statut de Prêtre) (24).",
        "euthanasia_threshold": "Seuil d'irrégularité ; les nouveau-nés difformes excédant ce taux sont éliminés à l'âge adulte (0.70).",
        "mutation_sigma": "Écart-type gaussien (σ) appliqué aux poids synaptiques lors du brassage génétique (0.08).",
        "crossover_rate": "Probabilité de recombinaison génétique équilibrée 50/50 entre les parents (0.50).",
        "morphology_annealing_enabled": "Interrupteur de physique géométrique — recuit polaire (r,φ), collision SAT et propriétés corporelles.",
        "annealing_decay_generations": "Générations requises pour que le recuit passe des gabarits d'Abbott à l'évolution libre (150).",
        "disease_enabled": "Interrupteur général des épidémies infectieuses et de la contagion interindividuelle.",
        "disease_outbreak_rate": "Probabilité d'émergence spontanée de peste en milieu surpeuplé par tick (0.00006).",
        "disease_rate": "Probabilité de transmission de la contagion à portée de contact (0.035).",
        "disease_energy_drain": "Perte d'énergie métabolique par tick pour chaque individu contaminé (0.05).",
        "disease_lethality": "Dégâts directs de santé (PV) infligés par tick par l'infection (0.18).",
        "weather_enabled": "Interrupteur des cycles météorologiques dynamiques (soleil, pluie, brume, orages).",
        "sleep_enabled": "Active le sommeil nocturne, le repos sous abri et la tradition orale à la nuit tombée.",
        "day_length": "Durée totale en ticks d'un cycle jour/nuit complet (1200).",
        "season_length": "Durée en ticks de chaque saison (Printemps, Été, Automne, Hiver) (12000).",
        "winter_food_mult": "Multiplicateur hivernal d'abondance alimentaire (0.70 doux, 0.50 rude, 0.30 critique).",
        "night_sight_mult": "Facteur réducteur de vision nocturne pour les castes diurnes (0.60).",
        "weather_change_rate": "Fréquence des transitions entre temps clair, pluie, brume et orage (0.002).",
        "weather_sickness_enabled": "Active l'hypothermie et le refroidissement en cas d'exposition prolongée aux intempéries.",
        "chill_drain": "Perte de vie directe par tick subie lors d'une exposition au froid sans toit (0.18).",
        "shelter_enabled": "Interrupteur de revendication des maisons, franchissement de portes et toitures.",
        "exposure_drain": "Perte d'énergie et de vie lors des intempéries hors de tout abri (0.025).",
        "house_capacity": "Nombre de places de couchage dans une halle (12) ; l'excédent dort à la belle étoile.",
        "house_decay_ticks": "Ticks avant qu'une maison abandonnée et sans toit ne tombe en ruine (10000).",
        "rest_recovery_mult": "Facteur de régénération de santé lors du sommeil sous un toit protecteur (2.0).",
        "territory_enabled": "Active le bornage frontalier, la garde territoriale et les pénalités d'intrusion.",
        "territory_radius": "Rayon d'influence territoriale d'un clan autour de ses habitations (16).",
        "trespass_decay": "Dégradation diplomatique par tick lorsqu'un clan rival franchit la frontière (0.15).",
        "max_clans": "Nombre maximal de clans souverains créés lors de la génération du monde (-1 = auto).",
        "totems_enabled": "Active les bénédictions des Totems d'Avatars Sacrés pour chaque colonie clanique.",
        "succession_enabled": "Permet la passation dynamique du commandement clanique à la mort du chef.",
        "communication_enabled": "Active les vocalises, cris d'alarme, chants de paix et bulles d'états d'âme.",
        "knowledge_enabled": "Active la mémoire spatiale, la cartographie des repères et les rumeurs partagées.",
        "schism_enabled": "Déclenche des scissions internes lorsque les membres manquent de vivres ou d'abris.",
        "schism_threshold": "Taux d'insatisfaction (faim, sans-abri) déclenchant une scission de faction (0.40).",
        "war_enabled": "Active les conflits armés entre clans rivaux, raids tactiques et conquêtes.",
        "attack_damage": "Dégâts de base infligés par les soldats lors des affrontements de clans (32.0).",
        "predation_enabled": "Active la dynamique proie-prédateur et le régime carnivore.",
        "predator_ratio": "Proportion de la population naissant avec l'instinct carnivore de chasse (0.02).",
        "hunt_radius": "Rayon de détection d'agression dans lequel prédateurs et guerriers ciblent leurs proies (16.0).",
        "bite_damage": "Dégâts physiques causés par morsure ou attaque prédatrice (28.0).",
        "energy_from_prey": "Gain calorique extrait de la capture et dévoration d'une proie (45.0).",
        "fear_radius": "Distance à laquelle herbivores et castes vulnérables fuient face au danger (12.0).",
        "coalitions_enabled": "Autorise les pactes de défense mutuelle et alliances diplomatiques entre clans amis.",
        "coalition_threshold": "Score de confiance mutuelle requis pour sceller une coalition défensive (40).",
        "leader_decisions_enabled": "Permet au chef de décréter des lois d'urgence (rationnement, loi martiale, guerre).",
        "resource_sharing_enabled": "Active les greniers collectifs et le partage altruiste de nourriture via les paniers.",
        "larder_capacity": "Capacité calorique des réserves collectives où sont déposés les surplus (300).",
        "cannibalism_enabled": "Autorise la consommation désespérée de chair en cas de famine extrême.",
        "eat_kin_enabled": "Permet de dévorer les dépouilles d'alliés au prix du bannissement et de vendettas.",
        "cannibalism_energy": "Énergie retirée de la consommation d'un congénère ou d'un ennemi terrassé (45.0).",
        "theology_enabled": "Active les 8 Avatars Sacrés, oratoires, temples, miracles et offrandes pieuses.",
        "tithe_rate": "Fraction d'énergie offerte aux sanctuaires à l'aube et au crépuscule pour la foi (0.04).",
        "temple_faith_cost": "Points de foi indispensables pour ériger un Temple resplendissant de la Sphère (400.0).",
        "age_enabled": "Active la succession des ères historiques (Âge d'Or, Glaciaire, Chaos, Peste).",
        "age_length": "Durée en ticks de chaque époque historique du monde (50000).",
        "culture_enabled": "Active les traditions, archétypes de gouvernement et diffusion culturelle.",
        "culture_spread_rate": "Vitesse d'adoption des traits culturels et dogmes entre clans voisins (0.0005).",
        "rivers_enabled": "Active les cours d'eau, gués, courants aquatiques, ponts et barrages.",
        "river_count": "Nombre de canaux fluviaux procéduraux façonnés à l'initialisation du monde (2).",
        "relief_enabled": "Active le dénivelé topographique, l'inertie des pentes, falaises et sentiers tassés.",
        "structural_enabled": "Active la dégradation des bâtiments par la météo, réparations et décombres.",
        "earthquake_enabled": "Permet des secousses sismiques ébranlant le relief et endommageant les édifices.",
        "earthquake_rate": "Fréquence des tremblements de terre lézardant les sols et structures (0.00008).",
        "lightning_enabled": "Déclenche de véritables éclairs orageux embrasant la végétation et blessant les êtres.",
        "lightning_strike_rate": "Fréquence des arcs électriques foudroyants lors des violentes tempêtes (0.0015).",
        "wildfire_enabled": "Permet la propagation d'incendies dévastateurs dans les forêts et fourrés secs.",
        "fire_rate": "Probabilité par tick qu'une plante prenne feu par temps sec ou foudre (0.00008).",
        "disaster_enabled": "Active météores cataclysmiques, crues subites et catastrophes majeures.",
        "disaster_rate": "Probabilité aléatoire d'avènement de calamités environnementales (0.0003).",
        "anomaly_count": "Nombre de zones d'anomalies spatiales déformant la physique locale (3).",
        "door_clearance": "Coefficient d'élargissement des ouvertures de portes selon la taille des créatures (1.5).",
    },
}

# ---------------------------------------------------------------------
# Re-export content translations from wiki_content_i18n
# ---------------------------------------------------------------------
from .wiki_content_i18n import (
    CODEBASE_MAP_MD_I18N,
    CONFIG_OPS_MD_I18N,
    CURL_EXAMPLES_I18N,
    DATA_MODEL_MD_I18N,
    HOW_IT_WORKS_MD_I18N,
)
