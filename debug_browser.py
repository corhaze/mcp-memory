from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Capture console messages
        def handle_console(msg):
            print(f"CONSOLE [{msg.type}]: {msg.text}")
        page.on("console", handle_console)
        
        # Capture unhandled exceptions
        def handle_error(err):
            print(f"ERROR: {err}")
        page.on("pageerror", handle_error)
        
        # Capture response types for /api/
        def handle_response(response):
            if "api/" in response.url:
                print(f"API RESPONSE: {response.url} {response.status} {response.headers.get('content-type')}")
        page.on("response", handle_response)
        
        print("Navigating to http://localhost:8000/")
        try:
            page.goto("http://localhost:8000/", wait_until="networkidle")
        except Exception as e:
            print(f"Navigation failed: {e}")
            
        print("Done.")
        browser.close()

if __name__ == "__main__":
    run()
