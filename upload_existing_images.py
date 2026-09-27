import os
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "MiniShop.settings"
)

django.setup()

from pathlib import Path
from django.core.files import File
from Shop.models import Product


MEDIA_PRODUCTS = (
    Path(__file__).resolve().parent
    / "media"
    / "products"
)


print("=" * 60)
print("UPLOADING EXISTING PRODUCT IMAGES TO CLOUDINARY")
print("=" * 60)


if not MEDIA_PRODUCTS.exists():

    print(
        f"ERROR: Folder not found:\n{MEDIA_PRODUCTS}"
    )

    raise SystemExit(1)


print(
    f"Product folder:\n{MEDIA_PRODUCTS}"
)


products = Product.objects.all()

print(
    f"Products found: {products.count()}"
)


for product in products:

    print("\n" + "-" * 60)

    print(f"Product ID : {product.id}")
    print(f"Product    : {product.name}")


    if not product.image:

        print("STATUS     : No image assigned")

        continue


    filename = Path(
        product.image.name
    ).name


    print(f"Filename   : {filename}")


    local_file = (
        MEDIA_PRODUCTS / filename
    )


    if not local_file.exists():

        print("STATUS     : Local file NOT FOUND")

        print(
            f"Expected   : {local_file}"
        )

        continue


    try:

        print("STATUS     : Uploading...")


        with open(
            local_file,
            "rb"
        ) as image_file:

            product.image.save(
                filename,
                File(image_file),
                save=True,
            )


        print("STATUS     : SUCCESS")

        print(
            f"Cloudinary : {product.image.url}"
        )


    except Exception as error:

        print("STATUS     : FAILED")

        print(
            f"ERROR      : {error}"
        )


print("\n" + "=" * 60)
print("UPLOAD PROCESS COMPLETED")
print("=" * 60)