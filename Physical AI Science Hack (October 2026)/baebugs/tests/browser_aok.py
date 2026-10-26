"""End-to-end evidence browser test. Local HTTP and Chrome only; no robots or external writes."""
import functools
import http.server
import json
import pathlib
import threading

from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]/"site/aok"
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    handler=functools.partial(Quiet,directory=str(ROOT))
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base="http://127.0.0.1:"+str(server.server_port)+"/"
    with sync_playwright() as engine:
        browser=engine.chromium.launch(headless=True,executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",args=["--no-sandbox"])
        results={}
        for width in (1440,390):
            page=browser.new_page(viewport={"width":width,"height":900})
            errs=[]
            page.on("pageerror",lambda e,errs=errs:errs.append(str(e)))
            page.goto(base,wait_until="domcontentloaded")
            page.wait_for_function("document.querySelector('#rootState').textContent.includes('PASS')",timeout=30000)
            assert page.locator("#snapshotCount").inner_text().startswith("247")
            page.locator("#typeFilter").select_option("part")
            page.locator("#search").fill("trommel_zone_2mm")
            assert page.locator("#resultsTotal").inner_text().startswith("1")
            page.locator(".result-item").first.click()
            assert "PASS" in page.locator("#inclusion").inner_text()
            page.locator('button[data-view="lab"]').click()
            page.locator("#labSelection").select_option("opentrons")
            assert page.locator("#labTitle").inner_text()=="Opentrons modular deck"
            page.locator('button[data-view="rights"]').click()
            assert page.locator("#rightsTable tr").count()==10
            page.locator('button[data-view="challenge"]').click()
            page.locator("#contestNode").select_option("claim:photo")
            page.locator("#counterClaim").fill("Independent manual labels have not been demonstrated")
            page.locator("#counterEvidence").fill("https://www.gbif.org/citation-guidelines")
            page.locator("#contestForm button[type=submit]").click()
            assert "fco:sha256" in page.locator("#contestPreview").inner_text()
            assert "github.com/biobitworks/baebugs/issues/new" in page.locator("#submitIssue").get_attribute("href")
            assert not errs,errs
            results[str(width)]={"graph_merkle":"PASS","search":"PASS","rights":"PASS","lab":"PASS","contest_FCO":"PASS","js_errors":0}
            page.close()
        browser.close()
    server.shutdown()
    print(json.dumps({"result":"PASS","viewports":results},indent=2))

if __name__=="__main__":main()
