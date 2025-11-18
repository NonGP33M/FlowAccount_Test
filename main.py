import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

app = FastAPI()

FILE_PATH = "products.json"
ALLOWED_CATEGORIES = {"อาหาร", "เครื่องดื่ม", "ของใช้", "อื่นๆ"}

class ProductIn(BaseModel):
    name: str
    sku: str
    price: float
    stock: int
    category: str

class ProductOut(ProductIn):
    id: int
    createdAt: str

# ----- Load DB -----
if os.path.exists(FILE_PATH):
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        db = [ProductOut(**x) for x in json.load(f)]
else:
    db = []

sku_set = {item.sku for item in db}

def save_db():
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump([item.dict() for item in db], f, ensure_ascii=False, indent=2)

# ----- POST /api/products -----
@app.post("/api/products", status_code=201)
def create_product(p: ProductIn):
    errors = []

    if not p.name.strip():
        errors.append("ชื่อสินค้าต้องไม่ว่าง")

    if not p.sku.strip():
        errors.append("รหัสสินค้าต้องไม่ว่าง")
    elif len(p.sku) < 3:
        errors.append("รหัสสินค้าต้องมีอย่างน้อย 3 ตัวอักษร")
    elif p.sku in sku_set:
        errors.append("รหัสสินค้าต้องไม่ซ้ำ")

    if p.price <= 0:
        errors.append("ราคาต้องมากกว่า 0")

    if p.stock < 0:
        errors.append("จำนวนสต็อกต้องไม่ติดลบ")

    if p.category not in ALLOWED_CATEGORIES:
        errors.append("หมวดหมู่ไม่ถูกต้อง")

    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    new = ProductOut(
        id=len(db) + 1,
        name=p.name,
        sku=p.sku,
        price=p.price,
        stock=p.stock,
        category=p.category,
        createdAt=datetime.utcnow().isoformat() + "Z"
    )

    db.append(new)
    sku_set.add(p.sku)
    save_db()

    return new


# ----- GET /api/products -----

@app.get("/api/products")
def list_products(category: Optional[str] = None):
    items = db
    if category:
        items = [p for p in items if p.category == category]
    return items


# ----- POST /api/products/sell -----
class SellRequest(BaseModel):
    productId: int
    quantity: int

@app.post("/api/products/sell")
def sell_product(req: SellRequest):
    if req.quantity <= 0:
        raise HTTPException(400, detail="quantity ต้องมากกว่า 0")

    product = next((p for p in db if p.id == req.productId), None)
    if not product:
        raise HTTPException(404, detail="ไม่พบสินค้า")

    if product.stock < req.quantity:
        raise HTTPException(400, detail="สต็อกไม่พอ")

    product.stock -= req.quantity
    save_db()

    return {
        "message": "ขายสำเร็จ",
        "productId": product.id,
        "remainingStock": product.stock
    }
