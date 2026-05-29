# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class PropertyItem(scrapy.Item):
    """Scraped property listing item — mirrors the database model fields."""

    # Source tracking
    source = scrapy.Field()            # e.g. "ddproperty", "hipflat", "fazwaz"
    source_id = scrapy.Field()         # Original listing ID from the source
    url = scrapy.Field()               # Permalink to the listing

    # Basic info
    title = scrapy.Field()             # Listing title
    description = scrapy.Field()       # Full description text
    property_type = scrapy.Field()     # e.g. "condo", "house", "townhouse", "land"
    listing_type = scrapy.Field()      # "rent" or "sale"

    # Price
    price = scrapy.Field()             # Numeric price value
    currency = scrapy.Field()          # e.g. "THB"
    price_unit = scrapy.Field()        # e.g. "month", "total", "sqm"
    original_price_text = scrapy.Field()  # Raw price text before parsing

    # Location
    location_name = scrapy.Field()     # Human-readable location/address
    province = scrapy.Field()          # e.g. "Chiang Mai"
    district = scrapy.Field()          # e.g. "Mueang Chiang Mai"
    subdistrict = scrapy.Field()       # e.g. "Chang Phueak"
    latitude = scrapy.Field()          # Decimal latitude
    longitude = scrapy.Field()         # Decimal longitude

    # Property details
    bedrooms = scrapy.Field()          # Number of bedrooms
    bathrooms = scrapy.Field()         # Number of bathrooms
    floor_area = scrapy.Field()        # Usable floor area (sqm)
    land_area = scrapy.Field()         # Land area (sqwa / sqm)
    floor_number = scrapy.Field()      # Floor number (condos)
    total_floors = scrapy.Field()      # Total floors in building
    furnishing = scrapy.Field()        # e.g. "Fully Furnished", "Semi-Furnished", "Unfurnished"
    year_built = scrapy.Field()        # Construction year
    parking = scrapy.Field()           # Number of parking spots

    # Amenities (list of strings)
    amenities = scrapy.Field()         # e.g. ["Swimming Pool", "Gym", "Security"]

    # Media
    images = scrapy.Field()            # List of image URLs
    image_urls = scrapy.Field()        # Scrapy Images Pipeline source field

    # Metadata
    listed_date = scrapy.Field()       # Date the listing was posted
    updated_date = scrapy.Field()      # Date the listing was last updated
    is_featured = scrapy.Field()       # Whether it's a featured/sponsored listing
    agent_name = scrapy.Field()        # Listing agent or agency name
    agent_phone = scrapy.Field()       # Contact phone
    agent_email = scrapy.Field()       # Contact email

    # Crawl metadata
    crawled_at = scrapy.Field()        # ISO timestamp when scraped
    checksum = scrapy.Field()          # Hash for deduplication
