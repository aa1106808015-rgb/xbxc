import re, json, io, os
src = open("data/recipes.js", encoding="utf-8").read()
m = re.search(r"window\.XIAOBAI_RECIPES\s*=\s*(\[.*\]);?\s*$", src, re.S)
data = json.loads(m.group(1))
print("dishes:", len(data))
for d in data:
    page = "recipes/%s.html" % d["slug"]
    html = open(page, encoding="utf-8").read()
    steps_html = html.count('class="step"')
    print(f'{d["id"]:10s} level={d["level"]} steps_data={len(d["steps"]):2d} steps_html={steps_html:2d} ingredients={len(d["ingredients"])} url={d["url"]}')
print("keys:", sorted(data[0].keys()))
print("ing keys:", sorted(data[0]["ingredients"][0].keys()))
print("step keys:", sorted(data[0]["steps"][0].keys()))
