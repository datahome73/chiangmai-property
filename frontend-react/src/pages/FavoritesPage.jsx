import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { NavBar, SwipeAction, Tag, Empty, Toast } from 'antd-mobile'
import usePropertyStore from '../stores/propertyStore'

export default function FavoritesPage() {
  const navigate = useNavigate()
  const favorites = usePropertyStore((s) => s.favorites)
  const loadFavorites = usePropertyStore((s) => s.loadFavorites)
  const toggleFavorite = usePropertyStore((s) => s.toggleFavorite)
  const getPriceLabel = usePropertyStore((s) => s.getPriceLabel)

  useEffect(() => {
    loadFavorites()
  }, [loadFavorites])

  const handleDelete = async (property) => {
    try {
      await toggleFavorite(property)
      Toast.show({ content: '已取消收藏', icon: 'success' })
    } catch (e) {
      Toast.show({ content: '操作失败', icon: 'fail' })
    }
  }

  const handleCardClick = (id) => {
    navigate(`/detail/${id}`)
  }

  const formatPrice = (val) => {
    if (!val) return ''
    if (val >= 10000) return `฿${(val / 10000).toFixed(1)}万`
    return `฿${val.toLocaleString()}`
  }

  const getPrice = (p) => {
    const val = p.price_type === 'RENT' ? p.price_rent : p.price_sale
    return formatPrice(val)
  }

  const getTypeLabel = (type) => {
    return { CONDO: '公寓', HOUSE: '别墅', TOWNHOUSE: '联排', APARTMENT: '普通公寓' }[type] || type || ''
  }

  // Empty state
  if (!favorites || favorites.length === 0) {
    return (
      <div style={{ background: '#f7f8fa', minHeight: '100vh' }}>
        <NavBar onBack={() => navigate(-1)}>我的收藏</NavBar>
        <Empty
          style={{ padding: '100px 0' }}
          description="还没有收藏的房源"
        />
        <div style={{ padding: '0 40px', textAlign: 'center' }}>
          <div
            style={{
              fontSize: 13,
              color: '#999',
              lineHeight: 1.6,
            }}
          >
            浏览房源时点击 ❤️ 按钮即可收藏
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ background: '#f7f8fa', minHeight: '100vh' }}>
      <NavBar onBack={() => navigate(-1)}>我的收藏</NavBar>
      <div className="favorites-content">
        <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
          共 {favorites.length} 个收藏房源
        </div>
        <div className="fav-grid">
          {favorites.map((property) => {
            const id = property.id || property.property_id
            const title = property.title || '房产标题'
            const image =
              property.images?.[0] || 'https://via.placeholder.com/400x280/667eea/ffffff?text=CM'
            const isRent = property.price_type === 'RENT'
            const price = getPrice(property)
            const typeLabel = getTypeLabel(property.property_type)

            return (
              <SwipeAction
                key={id}
                rightActions={[
                  {
                    key: 'delete',
                    text: '删除',
                    color: 'danger',
                    onClick: () => handleDelete(property),
                  },
                ]}
              >
                <div
                  className="fav-item-wrap"
                  onClick={() => handleCardClick(id)}
                >
                  <div className="property-card" style={{ marginBottom: 0 }}>
                    <img
                      className="property-card-img"
                      src={image}
                      alt={title}
                      loading="lazy"
                      style={{ height: 140 }}
                    />
                    <div className="property-card-body" style={{ padding: '8px 10px' }}>
                      <div
                        className={`property-card-price ${!isRent ? 'sale' : ''}`}
                        style={{ fontSize: 16, marginBottom: 2 }}
                      >
                        {price || '面议'}
                        <span className="property-card-price-unit">
                          {isRent ? '/月' : '（总价）'}
                        </span>
                      </div>
                      <div
                        className="property-card-title"
                        style={{
                          fontSize: 12,
                          minHeight: 32,
                          marginBottom: 4,
                        }}
                      >
                        {title}
                      </div>
                      <div className="property-card-meta" style={{ gap: 6, marginBottom: 4 }}>
                        <span>🛏 {property.bedrooms || '-'}</span>
                        <span>🚿 {property.bathrooms || '-'}</span>
                        {property.area_sqm && <span>📐 {property.area_sqm}m²</span>}
                      </div>
                      <div
                        className="property-card-footer"
                        style={{ paddingTop: 4 }}
                      >
                        <span className="property-card-source">
                          {property.source || '未知'}
                        </span>
                        {typeLabel && (
                          <Tag
                            color={isRent ? 'danger' : 'success'}
                            style={{ fontSize: 10 }}
                          >
                            {typeLabel}
                          </Tag>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </SwipeAction>
            )
          })}
        </div>
      </div>
    </div>
  )
}
