import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useT } from '../i18n'
import usePropertyStore from '../stores/propertyStore'
import useCompareStore from '../stores/compareStore'

export default function PropertyCard({ property, showActions = true }) {
  const navigate = useNavigate()
  const t = useT()
  const toggleFavorite = usePropertyStore((s) => s.toggleFavorite)
  const isFavorite = usePropertyStore((s) => s.isFavorite)
  const getPriceValue = usePropertyStore((s) => s.getPriceValue)
  const addItem = useCompareStore((s) => s.addItem)
  const removeItem = useCompareStore((s) => s.removeItem)
  const hasItem = useCompareStore((s) => s.hasItem)

  const price = getPriceValue(property)
  const isRent = property.price_type === 'RENT'
  const fav = isFavorite(property.id)
  const inCompare = hasItem(property.id)

  const formatPrice = (val) => {
    if (!val) return ''
    if (val >= 10000) return `${(val / 10000).toFixed(1)}万`
    return val.toLocaleString()
  }

  const typeLabel = property.property_type
    ? { CONDO: t('condo'), HOUSE: t('house'), TOWNHOUSE: t('townhouse'), APARTMENT: t('apartment') }[property.property_type] || property.property_type
    : ''

  return (
    <div className="property-card" onClick={() => navigate(`/detail/${property.id}`)}>
      <img
        className="property-card-img"
        src={property.images?.[0] || 'https://via.placeholder.com/400x280/667eea/ffffff?text=CM'}
        alt={property.title}
        loading="lazy"
      />
      <div className="property-card-body">
        <div className={`property-card-price ${!isRent ? 'sale' : ''}`}>
          {price ? `฿${formatPrice(price)}` : t('negotiable')}
          <span className="property-card-price-unit">{isRent ? t('perMonth') : t('totalPrice')}</span>
        </div>
        <div className="property-card-title">{property.title || t('propertyTitle')}</div>
        <div className="property-card-meta">
          <span>🛏 {property.bedrooms || '-'}{t('beds')}</span>
          <span>🚿 {property.bathrooms || '-'}{t('baths')}</span>
          <span>📐 {property.area_sqm || '-'}{t('sqm')}</span>
          {typeLabel && <span>{typeLabel}</span>}
        </div>
        <div className="property-card-footer">
          <span className="property-card-source">{property.source || t('unknownSource')}</span>
          {showActions && (
            <div className="property-card-actions">
              <span
                style={{ cursor: 'pointer', fontSize: '16px', color: fav ? '#ee0a24' : '#ccc' }}
                onClick={(e) => { e.stopPropagation(); toggleFavorite(property) }}
              >
                {fav ? '❤️' : '🤍'}
              </span>
              <span
                style={{ cursor: 'pointer', fontSize: '16px', color: inCompare ? '#1989fa' : '#ccc' }}
                onClick={(e) => {
                  e.stopPropagation()
                  inCompare ? removeItem(property.id) : addItem({ ...property })
                }}
              >
                📊
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
