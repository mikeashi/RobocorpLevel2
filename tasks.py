from robocorp.tasks import task
from robocorp import browser
from RPA.HTTP import HTTP
from RPA.Tables import Tables
from RPA.PDF import PDF
from RPA.Archive import Archive
import os
import time


@task
def order_robots_from_RobotSpareBin():
    cleanup()
    browser.configure()
    orders = get_orders()
    for order in orders:
        create_order(order)
        receipt = store_receipt_as_pdf(order["Order number"])
        screenshot = screenshot_robot(order["Order number"])
        embed_screenshot_to_receipt(screenshot, receipt)
    archive_receipts()
    cleanup()


def cleanup():
    """Cleanup output folders."""
    # create output folders if they don't exist
    if not os.path.exists("output/receipts"):
        os.makedirs("output/receipts")
    if not os.path.exists("output/tmp"):
        os.makedirs("output/tmp")

    for file in os.listdir("output/receipts"):
        os.remove(f"output/receipts/{file}")
    for file in os.listdir("output/tmp"):
        os.remove(f"output/tmp/{file}")


def download_orders_file(url):
    """Download orders file from given URL."""
    http = HTTP()
    http.download(url, "orders.csv", overwrite=True)


def get_orders():
    download_orders_file("https://robotsparebinindustries.com/orders.csv")
    return Tables().read_table_from_csv("orders.csv")


def open_robot_order_website():
    """Open browser and navigate to order form."""
    browser.goto("https://robotsparebinindustries.com")
    browser.goto("https://robotsparebinindustries.com/#/robot-order")
    close_popup_if_exists()


def close_popup_if_exists():
    """Close popup if it exists."""
    page = browser.page()
    try:
        page.eval_on_selector(
            ".modal-content", "el => el.querySelector('button').click()"
        )
    except Exception:
        # Popup did not exist
        pass


def fill_order_form(order):
    page = browser.page()

    # Select head by value
    page.select_option("#head", order["Head"])

    # check body by id
    page.check(f"#id-body-{order['Body']}")

    # type legs
    page.type("input[placeholder='Enter the part number for the legs']", order["Legs"])

    # type address
    page.type("#address", order["Address"])


def download_robot_image():
    page = browser.page()
    page.click("#preview")
    # screenshot robot-preview-image


def submit_order():
    page = browser.page()
    page.click("#order")

    try:
        if page.wait_for_selector("#receipt", timeout=3000):
            print("Order was submited")
            return True
        else:
            print("Order was not submited")
            raise Exception("Order was not submited")
    except:
        return False


def create_order(order):
    """Create order for given robot."""
    submited = False
    while not submited:
        print("Creating order for robot: ", order)
        open_robot_order_website()
        fill_order_form(order)
        download_robot_image()
        submited = submit_order()


def store_receipt_as_pdf(order_number):
    pdf = PDF()
    path = f"output/receipts/{order_number}.pdf"
    page = browser.page()
    receipt = page.inner_html("#receipt")
    pdf.html_to_pdf(receipt, path)
    return path


def screenshot_robot(order_number):
    page = browser.page()
    image = page.locator("#robot-preview-image")
    screenshot_path = f"output/tmp/{order_number}.png"
    image = browser.screenshot(image)
    with open(screenshot_path, "wb") as file:
        file.write(image)
    return screenshot_path


def embed_screenshot_to_receipt(screenshot, pdf_file):
    pdf = PDF()
    pdf.add_files_to_pdf(
        files=[
            pdf_file,
            screenshot + ":align=center",
        ],
        target_document=pdf_file,
    )


def archive_receipts():
    """Archive receipts to zip file."""
    archive = Archive()
    date = time.strftime("%Y-%m-%d-%H-%M-%S")

    archive.archive_folder_with_zip("output/receipts", f"output/receipts-{date}.zip")
