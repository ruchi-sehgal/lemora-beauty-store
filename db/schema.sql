DROP TABLE IF EXISTS products;

CREATE TABLE products (
    sku_id             text PRIMARY KEY,
    brand              text NOT NULL,
    name               text NOT NULL,
    category           text NOT NULL,
    product_type       text NOT NULL,
    fragrance_family   text,
    gender             text,
    benefit            text,
    key_ingredients    text,
    fragrance_notes    text,
    skin_types         text[] NOT NULL DEFAULT '{}',
    concerns           text[] NOT NULL DEFAULT '{}',
    target_audience    text,
    price_sgd          numeric(10,2) NOT NULL CHECK (price_sgd > 0),
    price_is_demo      boolean NOT NULL DEFAULT true,
    ingredients_status text NOT NULL,
    is_active          boolean NOT NULL DEFAULT true
);