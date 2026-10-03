from pdf2image import convert_from_path
import os

POPPLER_PATH = r"D:\codes\ncert-img\poppler\Library\bin"

def pdf_to_images(pdf_path: str):

    output_dir = os.path.abspath("uploads/pages")
    os.makedirs(output_dir, exist_ok=True)

    print("PDF:", os.path.abspath(pdf_path))
    print("Output directory:", output_dir)

    images = convert_from_path(
        pdf_path,
        poppler_path=POPPLER_PATH,
        dpi=200
    )

    print("Number of pages:", len(images))

    image_paths = []

    for i, image in enumerate(images):

        path = os.path.join(
            output_dir,
            f"page_{i + 1}.png"
        )

        image.save(path, "PNG")

        print("Saved:", path)
        print("Exists:", os.path.exists(path))

        image_paths.append(path)

    return image_paths