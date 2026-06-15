import React, { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { NavBar, SearchBar, Tabs, Tag, Grid, Empty, DotLoading } from 'antd-mobile'
import usePropertyStore from '../stores/propertyStore'
import { useT } from '../i18n'

const priceTypeLabelMap = {
  '': '全部',
  RENT: '出租',
  SALE: '出售',
}

function PropertyCard({ property, onClick }) {
  const store = usePropertyStore()
  const priceLabel = store.getPriceLabel(property)
  const isSale = property.price_type === 'SALE'

  return (
    <div className="property-card" onClick={() => onClick?.(property)}>
      <img
        className="property-card-img"
        src={property.images?.[0] || property.image || 'https://via.placeholder.com/300x200?text=No+Image'}
        alt={property.title}
        onError={(e) => { e.target.src = 'https://via.placeholder.com/300x200?text=No+Image' }}
      />
      <div className="property-card-body">
        <div className={`property-card-price ${isSale ? 'sale' : ''}`}>
          {priceLabel}
        </div>
        <div className="property-card-title">{property.title}</div>
        <div className="property-card-meta">
          <span>
            {property.bedrooms ? `${property.bedrooms}室` : ''}
            {property.bedrooms && property.area_sqm ? ' | ' : ''}
            {property.area_sqm ? `${property.area_sqm}㎡` : ''}
          </span>
        </div>
        <div className="property-card-footer">
          <span className="property-card-source">{property.source || ''}</span>
        </div>
      </div>
    </div>
  )
}

export default function HomePage() {
  const t = useT()
  const navigate = useNavigate()
  const {
    properties,
    totalCount,
    loading,
    filters,
    districts,
    loadProperties,
    refreshProperties,
    setFilters,
    fetchDistricts,
  } = usePropertyStore()

  useEffect(() => {
    fetchDistricts()
    loadProperties(1)
  }, [])

  const handleTabChange = useCallback((key) => {
    const priceType = key === 'all' ? '' : key.toUpperCase()
    setFilters({ priceType })
    refreshProperties()
  }, [setFilters, refreshProperties])

  const handleSearch = useCallback(() => {
    navigate('/search')
  }, [navigate])

  const handleDistrictClick = useCallback((district) => {
    setFilters({ district: district.id || district.name })
    navigate('/search')
  }, [navigate, setFilters])

  const handlePropertyClick = useCallback((property) => {
    navigate(`/detail/${property.id}`)
  }, [navigate])

  const currentTab = filters.priceType
    ? filters.priceType.toLowerCase()
    : 'all'

  return (
    <div style={{ background: '#f7f8fa', minHeight: '100vh' }}>
      {/* Search Bar */}
      <div style={{ background: '#fff', padding: '12px 16px', position: 'sticky', top: 0, zIndex: 10 }}>
        <SearchBar
          shape="round"
          placeholder={t('searchPlaceholder')}
          onFocus={handleSearch}
          readOnly
        />
      </div>

      {/* Tabs */}
      <Tabs
        activeKey={currentTab}
        onChange={handleTabChange}
        style={{ background: '#fff' }}
      >
        <Tabs.Tab title={t('all')} key="all" />
        <Tabs.Tab title={t('rent')} key="rent" />
        <Tabs.Tab title={t('sale')} key="sale" />
      </Tabs>

      {/* Hot Districts */}
      {districts.length > 0 && (
        <div style={{ background: '#fff', marginTop: 10, padding: '16px 16px 12px' }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#333', marginBottom: 12 }}>
            {t('hotDistricts')}
          </div>
          <Grid columns={4} gap={8}>
            {districts.slice(0, 8).map((d, idx) => (
              <Grid.Item key={d.id || idx}>
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    padding: '8px 0',
                    background: '#f7f8fa',
                    borderRadius: 8,
                    cursor: 'pointer',
                  }}
                  onClick={() => handleDistrictClick(d)}
                >
                  <span style={{ fontSize: 14, fontWeight: 500, color: '#333' }}>
                    {d.name}
                  </span>
                  <span style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                    {d.count || d.property_count || 0} {t('properties')}
                  </span>
                </div>
              </Grid.Item>
            ))}
          </Grid>
        </div>
      )}

      {/* Property List */}
      <div style={{ padding: '12px 12px 0' }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: '#333', marginBottom: 12 }}>
          {t('recommended')}
        </div>
        {loading && properties.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <DotLoading color="primary" />
            <div style={{ color: '#999', fontSize: 13, marginTop: 8 }}>{t('loading')}</div>
          </div>
        ) : properties.length === 0 ? (
          <Empty description={t('noData')} />
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 8,
            }}
          >
            {properties.map((p) => (
              <PropertyCard key={p.id} property={p} onClick={handlePropertyClick} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
