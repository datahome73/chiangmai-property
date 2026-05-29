import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { NavBar, Button, Tag, Toast, Empty, Dialog } from 'antd-mobile'
import useCompareStore from '../stores/compareStore'
import usePropertyStore from '../stores/propertyStore'
import { fetchPropertyCompare } from '../api'
import { useT } from '../i18n'

const COMPARE_FIELDS = [
  { key: 'images', labelKey: 'image' },
  { key: 'price', labelKey: 'price' },
  { key: 'bedrooms', labelKey: 'bedrooms' },
  { key: 'bathrooms', labelKey: 'bathrooms' },
  { key: 'area_sqm', labelKey: 'area_sqm' },
  { key: 'property_type', labelKey: 'property_type' },
  { key: 'floor', labelKey: 'floor_label' },
  { key: 'decoration', labelKey: 'decoration_label' },
  { key: 'district', labelKey: 'district' },
  { key: 'source', labelKey: 'source_label' },
]

const TYPE_LABELS = {
  CONDO: '公寓',
  HOUSE: '别墅',
  TOWNHOUSE: '联排',
  APARTMENT: '普通公寓',
}

export default function ComparePage() {
  const navigate = useNavigate()
  const t = useT()
  const items = useCompareStore((s) => s.items)
  const count = useCompareStore((s) => s.count)
  const removeItem = useCompareStore((s) => s.removeItem)
  const clearAll = useCompareStore((s) => s.clearAll)
  const addItem = useCompareStore((s) => s.addItem)

  const properties = usePropertyStore((s) => s.properties)
  const loadProperties = usePropertyStore((s) => s.loadProperties)
  const getPriceValue = usePropertyStore((s) => s.getPriceValue)
  const getPriceLabel = usePropertyStore((s) => s.getPriceLabel)

  const [selectVisible, setSelectVisible] = useState(false)

  // Load more properties for selection
  useEffect(() => {
    if (properties.length === 0) {
      loadProperties(1)
    }
  }, [])

  // Determine best-price columns
  const bestRentIdx = (() => {
    if (count === 0) return -1
    const rentItems = items
      .map((item, idx) => ({ idx, rent: item.price_type === 'RENT' ? getPriceValue(item) : null }))
      .filter((x) => x.rent !== null && x.rent > 0)
    if (rentItems.length === 0) return -1
    const minRent = Math.min(...rentItems.map((x) => x.rent))
    return rentItems.find((x) => x.rent === minRent)?.idx ?? -1
  })()

  const bestSaleIdx = (() => {
    if (count === 0) return -1
    const saleItems = items
      .map((item, idx) => ({ idx, sale: item.price_type !== 'RENT' ? getPriceValue(item) : null }))
      .filter((x) => x.sale !== null && x.sale > 0)
    if (saleItems.length === 0) return -1
    const minSale = Math.min(...saleItems.map((x) => x.sale))
    return saleItems.find((x) => x.sale === minSale)?.idx ?? -1
  })()

  const getFieldValue = (item, fieldKey) => {
    switch (fieldKey) {
      case 'images':
        return null // handled separately
      case 'price':
        return getPriceLabel(item)
      case 'bedrooms':
        return item.bedrooms ? `${item.bedrooms}室` : '-'
      case 'bathrooms':
        return item.bathrooms ? `${item.bathrooms}卫` : '-'
      case 'area_sqm':
        return item.area_sqm ? `${item.area_sqm}m²` : '-'
      case 'property_type':
        return TYPE_LABELS[item.property_type] || item.property_type || '-'
      case 'floor':
        return item.floor ? `${item.floor}层` : '-'
      case 'decoration':
        return item.decoration || '-'
      case 'district':
        return item.district || '-'
      case 'source':
        return item.source || '-'
      default:
        return '-'
    }
  }

  const handleAddProperty = (property) => {
    if (count >= 4) {
      Toast.show({ content: t('maxCompare'), icon: 'fail' })
      return
    }
    addItem({ ...property })
    setSelectVisible(false)
    Toast.show({ content: t('addedToCompare'), icon: 'success' })
  }

  const handleRemove = (id) => {
    removeItem(id)
  }

  const handleClearAll = () => {
    Dialog.confirm({
      content: t('confirmClear'),
      onConfirm: () => clearAll(),
    })
  }

  const availableProperties = properties.filter((p) => !items.some((i) => i.id === p.id))

  // Empty state
  if (count === 0) {
    return (
      <div className="compare-view">
        <NavBar onBack={() => navigate(-1)}>{t('propertyCompare')}</NavBar>
        <Empty
          style={{ padding: '80px 0' }}
          description={t('noCompareItems')}
        />
        <div style={{ padding: '0 16px' }}>
          <Button
            block
            color="primary"
            size="large"
            onClick={() => {
              if (properties.length === 0) loadProperties(1)
              setSelectVisible(true)
            }}
          >
            {t('addProperty')}
          </Button>
        </div>

        {/* Property select dialog */}
        <Dialog
          visible={selectVisible}
          onClose={() => setSelectVisible(false)}
          content={
            <div style={{ maxHeight: '50vh', overflowY: 'auto' }}>
              {availableProperties.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                  {t('noMoreAdd')}
                </div>
              ) : (
                availableProperties.slice(0, 20).map((p) => (
                  <div
                    key={p.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '10px 0',
                      borderBottom: '1px solid #f0f0f0',
                      cursor: 'pointer',
                    }}
                    onClick={() => handleAddProperty(p)}
                  >
                    <img
                      src={p.images?.[0] || 'https://via.placeholder.com/60x60/667eea/ffffff?text=CM'}
                      alt=""
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: 6,
                        objectFit: 'cover',
                        marginRight: 10,
                      }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: 13,
                          color: '#333',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {p.title || '房产标题'}
                      </div>
                      <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>
                        {getPriceLabel(p)}
                      </div>
                    </div>
                    <Button size="small" color="primary" fill="none">
                      {t('addProperty')}
                    </Button>
                  </div>
                ))
              )}
            </div>
          }
          actions={[
            [
              {
                key: 'cancel',
                text: t('cancel'),
                onClick: () => setSelectVisible(false),
              },
            ],
          ]}
        />
      </div>
    )
  }

  return (
    <div className="compare-view">
      <NavBar onBack={() => navigate(-1)}>{t('propertyCompare')}</NavBar>

      {/* Header */}
      <div className="compare-header">
        <div className="header-info">
          <span>📋</span>
          <span>{t('selected')} {count}{t('of')}4 {t('items')}</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button size="small" color="primary" onClick={() => {
            if (properties.length === 0) loadProperties(1)
            setSelectVisible(true)
          }}>
            {t('addProperty')}
          </Button>
          <Button size="small" onClick={handleClearAll}>
            {t('clearAll')}
          </Button>
        </div>
      </div>

      {/* Compare Table */}
      <div className="compare-table-wrap">
        <div className="compare-table">
          {/* Header row: image + property name/tag */}
          <div className="table-row row-header">
            <div className="cell-label">{t('propertyCompare')}</div>
            {items.map((item, idx) => (
              <div className="cell-value" key={item.id}>
                <div className="cell-img-wrap">
                  <img
                    className="cell-img"
                    src={item.images?.[0] || 'https://via.placeholder.com/200x120/667eea/ffffff?text=CM'}
                    alt={item.title}
                  />
                  <Tag
                    className="remove-tag"
                    color="default"
                    style={{ position: 'absolute', top: 4, right: 4, zIndex: 2 }}
                    onClick={() => handleRemove(item.id)}
                  >
                    ✕
                  </Tag>
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: '#333',
                    marginTop: 4,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    maxWidth: '100%',
                  }}
                >
                  {item.title || '房产标题'}
                </div>
                <Tag
                  color={item.price_type === 'RENT' ? 'danger' : 'success'}
                  style={{ marginTop: 4 }}
                >
                  {item.price_type === 'RENT' ? t('rent') : t('sale')}
                </Tag>
              </div>
            ))}
          </div>

          {/* Field rows */}
          {COMPARE_FIELDS.filter((f) => f.key !== 'images').map((field) => (
            <div className="table-row" key={field.key}>
              <div className="cell-label">{t(field.labelKey)}</div>
              {items.map((item, idx) => {
                let cellClass = 'cell-value'
                if (field.key === 'price') {
                  if (item.price_type === 'RENT' && idx === bestRentIdx) {
                    cellClass += ' best-rent'
                  } else if (item.price_type !== 'RENT' && idx === bestSaleIdx) {
                    cellClass += ' best-sale'
                  }
                }
                return (
                  <div className={cellClass} key={item.id}>
                    {getFieldValue(item, field.key)}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Property select dialog */}
      <Dialog
        visible={selectVisible}
        onClose={() => setSelectVisible(false)}
        content={
          <div style={{ maxHeight: '50vh', overflowY: 'auto' }}>
            {availableProperties.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                {t('noMoreAdd')}
              </div>
            ) : (
              availableProperties.slice(0, 20).map((p) => (
                <div
                  key={p.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '10px 0',
                    borderBottom: '1px solid #f0f0f0',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleAddProperty(p)}
                >
                  <img
                    src={p.images?.[0] || 'https://via.placeholder.com/60x60/667eea/ffffff?text=CM'}
                    alt=""
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 6,
                      objectFit: 'cover',
                      marginRight: 10,
                    }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 13,
                        color: '#333',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {p.title || '房产标题'}
                    </div>
                    <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>
                      {getPriceLabel(p)}
                    </div>
                  </div>
                  <Button size="small" color="primary" fill="none">
                    {t('addProperty')}
                  </Button>
                </div>
              ))
            )}
          </div>
        }
        actions={[
          [
            {
              key: 'cancel',
              text: t('cancel'),
              onClick: () => setSelectVisible(false),
            },
          ],
        ]}
      />
    </div>
  )
}
