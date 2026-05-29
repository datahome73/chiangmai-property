import React from 'react'
import { useNavigate } from 'react-router-dom'
import usePropertyStore from '../stores/propertyStore'
import useCompareStore from '../stores/compareStore'

export default function PropertyCard({ property, showActions = true }) {
  const navigate = useNavigate()
  const toggleFavorite = usePropertyStore((s) => s.toggleFavorite)
  const isFavorite = usePropertyStore((s) => s.isFavorite)
  const getPriceValue = usePropertyStore((s) => s.getPriceValue)
  const addItem = useCompareStore((s) => s.addItem)
  const removeItem = useCompareStore((s) => s.removeItem)
  const hasItem = useCompareStore((s) => s.hasItem)
  const compareCount = useCompareStore((s) => s.count)

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
    ? { CONDO: '公寓', HOUSE: '别墅', TOWNHOUSE: '联排', APARTMENT: '普通公寓' }[property.property_type] || property.property_type
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
          {price ? `฿${formatPrice(price)}` : '面议'}
          <span className="property-card-price-unit">{isRent ? '/月' : '（总价）'}</span>
        </div>
        <div className="property-card-title">{property.title || '房产标题'}</div>
        <div className="property-card-meta">
          <span>🛏 {property.bedrooms || '-'}室</span>
          <span>🚿 {property.bathrooms || '-'}卫</span>
          <span>📐 {property.area_sqm || '-'}m²</span>
          {typeLabel && <span>{typeLabel}</span>}
        </div>
        <div className="property-card-footer">
          <span className="property-card-source">{property.source || '未知来源'}</span>
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
