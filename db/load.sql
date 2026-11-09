TRUNCATE products;

CREATE TEMP TABLE staging (
    sku_id text, brand text, name text, category text, product_type text,
    fragrance_family text, gender text, benefit text, key_ingredients text,
    fragrance_notes text, skin_types text, concerns text, target_audience text,
    price_sgd text, price_is_demo text, ingredients_status text
);

\copy staging FROM 'data/products_seed.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO products
SELECT sku_id, brand, name, category, product_type, fragrance_family, gender,
       benefit, key_ingredients, fragrance_notes,
       COALESCE(string_to_array(skin_types, '|'), '{}'),
       COALESCE(string_to_array(concerns, '|'), '{}'),
       target_audience, price_sgd::numeric, price_is_demo::boolean, ingredients_status
FROM staging;