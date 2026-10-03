from app.services.preprocessing import pdf_to_images

images = pdf_to_images("test_marksheet.pdf")

print("\nGenerated images:")

for image in images:
    print(image)