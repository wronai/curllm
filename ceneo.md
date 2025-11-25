
🤖 ═══ LLM-GUIDED ATOMIC EXTRACTOR ═══


🤖 LLM Decision: Step 1: Identify Container Selector

   Asking LLM...

🤖 LLM Decision: Container Selector Decision

```json
{
  "text": "{\n  \"selector\": \".page-body .js_popupContainer.product-container\",\n  \"reasoning\": \"The 'page-body' class is present in one of the sample elements, which likely contains product information. The 'js_popupContainer' class might be specific to product containers as it could indicate a popup or modal containing product details. Additionally, assuming there's a common class like 'product-container' for all products, this selector targets those specifically.\"\n}"
}
```

⚠️ LLM-Guided Extractor returned no data: LLM couldn't identify container

🔄 Iterative Extractor enabled - trying atomic DOM queries


🔄 ═══ ITERATIVE EXTRACTOR ═══


💰 Price limit detected: 550.0 zł

🔍 Step 1: Quick Page Check

   Running fast indicators check...

🔍 Quick Check Results

```json
{
  "has_prices": true,
  "price_count": 52,
  "has_product_links": true,
  "product_link_count": 230,
  "has_list_structure": true,
  "total_links": 347,
  "page_type": "product_listing"
}
```

🔍 Step 2: Container Structure Detection

   Looking for product_listing containers...

🔍 Container Detection Results

```json
{
  "found": true,
  "candidates": [
    {
      "selector": ".cat-prod-row",
      "count": 32,
      "has_link": true,
      "has_price": true,
      "has_image": true,
      "classes": "cat-prod-row js_analytics-promotedItem promoted-offer",
      "sample_text": "OFERTA SPECJALNA Shark Stratos Odkurzacz bezprzewodowy IZ400EUTDB\nKategoria: Urządzenia sprzątające\n"
    }
  ],
  "best": {
    "selector": ".cat-prod-row",
    "count": 32,
    "has_link": true,
    "has_price": true,
    "has_image": true,
    "classes": "cat-prod-row js_analytics-promotedItem promoted-offer",
    "sample_text": "OFERTA SPECJALNA Shark Stratos Odkurzacz bezprzewodowy IZ400EUTDB\nKategoria: Urządzenia sprzątające\n"
  }
}
```

🔍 Step 3: Field Location Detection

   Analyzing fields in .cat-prod-row...

🔍 Field Detection Results

```json
{
  "found": true,
  "fields": {
    "name": {
      "selector": "a.go-to-shop",
      "sample": "Shark Stratos Odkurzacz bezprzewodowy IZ400EUTDB"
    },
    "price": {
      "selector": "span.price-format",
      "sample": "899,99zł",
      "value": 899.99
    },
    "url": {
      "selector": "a[href]",
      "sample": "https://www.ceneo.pl/Click/Offer/?e=_7iXc5yj4Rh1GbvzQOmAfvPlmmavR38JNwo5z5SYjZJzT1Z01nXu0RUUc1qbbKz-u6nFbe93D9wuAvJxCRoP1OvR95YYaUl2K4BaH__g9yYW0o4qz8BTV7506LhsOVYNsaldK4eljAm0qWBW03q8dS59rg21Nlh1N2VcFemLac9f0331J4wNBD8PIpalIfzQvEHtFEw0QPsbPfGu09LCtMncoGq3fDggpVBMwlkFDd2lUEzCWQUN3bl05r4sm0_miL0PeXqwEAWlUEzCWQUN3aVQTMJZBQ3dLkFMo7MyZE9G5kA55NoDBMLECYSLAo9bGgRrxhvvHECYgPFeXpymP2A_ZLGSon_40c_SY8C3NEwHoLNq9XRpFfUGkHfWe6ezRCag4pWuTS9XbcaPBsfsBu845c6yubZ8ZNbGv8mgU5Oudx1FTokCCxP7ScEiaVaK&ctx=CgsIjO_NvtSc1j4QBRIkZTFjMGE2MmUtY2EyOC0xMWYwLTkxNDYtZDkyN2Q4YjA3YTM1GiRiNzY2MzZjOC1jYTQ0LTExZjAtODg3Ni04M2QxNjMxNTc5M2I=&a=2"
    }
  },
  "completeness": 1
}
```

🔍 Step 4: Data Extraction

   Extracting up to 50 items using strategy...

🔍 Extraction Results

```json
{
  "count": 32,
  "sample": [
    {
      "name": "OFERTA SPECJALNA Shark Stratos Odkurzacz bezprzewodowy IZ400EUTDB\nKategoria: Urządzenia sprzątające\nRodzaj: Odkurzacze bateryjne",
      "price": 899.99,
      "url": "https://www.ceneo.pl/Click/Offer/?e=_7iXc5yj4Rh1GbvzQOmAfvPlmmavR38JNwo5z5SYjZJzT1Z01nXu0RUUc1qbbKz-u6nFbe93D9wuAvJxCRoP1OvR95YYaUl2K4BaH__g9yYW0o4qz8BTV7506LhsOVYNsaldK4eljAm0qWBW03q8dS59rg21Nlh1N2VcFemLac9f0331J4wNBD8PIpalIfzQvEHtFEw0QPsbPfGu09LCtMncoGq3fDggpVBMwlkFDd2lUEzCWQUN3bl05r4sm0_miL0PeXqwEAWlUEzCWQUN3aVQTMJZBQ3dLkFMo7MyZE9G5kA55NoDBMLECYSLAo9bGgRrxhvvHECYgPFeXpymP2A_ZLGSon_40c_SY8C3NEwHoLNq9XRpFfUGkHfWe6ezRCag4pWuTS9XbcaPBsfsBu845c6yubZ8ZNbGv8mgU5Oudx1FTokCCxP7ScEiaVaK&ctx=CgsIjO_NvtSc1j4QBRIkZTFjMGE2MmUtY2EyOC0xMWYwLTkxNDYtZDkyN2Q4YjA3YTM1GiRiNzY2MzZjOC1jYTQ0LTExZjAtODg3Ni04M2QxNjMxNTc5M2I=&a=2"
    },
    {
      "name": "OFERTA SPECJALNA Shark StainStriker HairPro odkurzacz pioracy PX250EUT\nKategoria: Urządzenia sprzątające\nRodzaj: Odkurzacze przemysłowe",
      "price": 749.99,
      "url": "https://www.ceneo.pl/Click/Offer/?e=ty1IvXT_aOZ1GbvzQOmAfvPlmmavR38JNwo5z5SYjZJzT1Z01nXu0dyx4ZjglisRicIXQ5GHzg4N2V6mL8CffAI3TAglLpjkNF4dhLf3ubSl7OlcIjuhgaNU4ZBKR3pvBKYFVNIqxGjvQSkPwXzY1n-OmWLZJyy28GIgeoUNpO0KE4FvhC5dfRKx0hYjJMnl3Ymsq5JR2Lx6QL5bd4PjjqRiy3VaDTqFiH7VxwqW3a6lUEzCWQUN3Q7q8m3sgx-Ahh3QM0f2Y8ClUEzCWQUN3aVQTMJZBQ3dMzkKo7pWV4hSN60-XMdyXbE13KS5Nt0Iq7osHGqZZQquaLaR1uS7PWJCs78KlY4_Je2xq1FKh_Ux2j617tPD63DoYRsp6xwFGpYP0xrALG9YLi3vv_0oVqcl7Mokdmlxrvf3EDi-SpCXPkFvuLw5IeyGSkEhV6Bx&ctx=CgsIjO_NvtSc1j4QBRIkZTFjMGE2MmUtY2EyOC0xMWYwLTkxNDYtZDkyN2Q4YjA3YTM1GiRiNzY2MzZjOC1jYTQ0LTExZjAtODg3Ni04M2QxNjMxNTc5M2I=&a=2"
    },
    {
      "name": "SHARK S1000EU\n 5,0\n/ 5\n4 opinie\nDodaj do ulubionych\nKolor: Białe\nMoc: 1050 W\nod349,00zł\nPORÓWNAJ CENY\nw 7 sklepach\nDarmowa wysyłka\nw 7 ofertach\nlub z",
      "price": 349,
      "url": "https://www.ceneo.pl/102723109##;02514#tag=nph_row_promotion"
    }
  ]
}
```

💰 Price Filter Applied: 32 → 14 products (removed 18 above 550.0 zł)

✅ Iterative Extractor succeeded - found 14 items

Validation pass applied.

```json
{
  "products": [
    {
      "name": "SHARK S1000EU\n 5,0\n/ 5\n4 opinie\nDodaj do ulubionych\nKolor: Białe\nMoc: 1050 W",
      "price": 349,
      "url": "https://www.ceneo.pl/102723109##;02514#tag=nph_row_promotion"
    },
    {
      "name": "Bosch UniversalBrush 06033E0000\n 4,5\n/ 5\n33 opinie\n10+ kupionych ostatnio",
      "price": 168.3,
      "url": "https://www.ceneo.pl/110631727"
    },
    {
      "name": "Bosch EasyVac 3 06033D1000\n 4,3\n/ 5\n5 opinii",
      "price": 349,
      "url": "https://www.ceneo.pl/52315916"
    },
    {
      "name": "Bosch AdvancedVac 18V-8 06033E1000\nNapisz opinię",
      "price": 317.99,
      "url": "https://www.ceneo.pl/118147335"
    },
    {
      "name": "Bosch UniversalVac 15 06033D1100\n 4,6\n/ 5\n11 opinii",
      "price": 338.9,
      "url": "https://www.ceneo.pl/52782460"
    },
    {
      "name": "Bosch UniversalBrush 06033E0002\n 5,0\n/ 5\n1 opinia",
      "price": 182.02,
      "url": "https://www.ceneo.pl/158836315"
    }
  ]
}
```

⚠️  WARNING: Zero steps executed

✓ SUCCESS: Task completed (0 steps taken)

✅ Run finished successfully: Task completed successfully (0 steps taken)

