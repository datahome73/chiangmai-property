import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  SearchBar, Tabs, Tag, Button,
  PullToRefresh, InfiniteScroll, Empty, DotLoading,
  Popup, Input,
} from 'antd-mobile'
import usePropertyStore from '../stores/propertyStore'
import PropertyCard from '../components/PropertyCard'

const BEDROOM_OPTIONS = [
  { label: '全部', value: '' },
  { label: '1室', value: '1' },
  { label: '2室', value: '2' },
  { label: '3室', value: '3' },
  { label: '4室', value: '4' },
  { label: '5室+', value: '5' },
]

const SOURCE_OPTIONS = [
  { label: '全部来源', value: '' },
  { label: 'HipFlat', value: 'hipflat' },
  { label: 'FazWaz', value: 'fazwaz' },
  { label: 'DDProperty', value: 'ddproperty' },
]

const SORT_OPTIONS = [
  { label: '默认排序', value: '' },
  { label: '价格从低到高', value: 'price_asc' },
  { label: '价格从高到低', value: 'price_desc' },
  { label: '面积从大到小', value: 'area_desc' },
  { label: '最新发布', value: 'newest' },
]

export default function SearchPage() {
  const navigate = useNavigate()
  const store = usePropertyStore()
  const { properties, totalCount, loading, finished, districts, filters } = store
  const [keyword, setKeyword] = useState(filters.keyword || '')
  const [priceTab, setPriceTab] = useState('')
  const [bedrooms, setBedrooms] = useState('')
  const [filterVisible, setFilterVisible] = useState(false)

  // Local filter states
  const [localDistrict, setLocalDistrict] = useState('')
  const [localMinPrice, setLocalMinPrice] = useState('')
  const [localMaxPrice, setLocalMaxPrice] = useState('')
  const [localSource, setLocalSource] = useState('')
  const [localSort, setLocalSort] = useState('')

  const loadProperties = useCallback((page = 1, append = false) => {
    store.loadProperties(page, append)
  }, [store])

  const refreshProperties = useCallback(async () => {
    await store.refreshProperties()
  }, [store])

  const loadMore = useCallback(async () => {
    await store.loadProperties(store.currentPage + 1, true)
  }, [store])

  useEffect(() => {
    store.fetchDistricts()
    loadProperties(1)
  }, [])

  const handleSearch = () => {
    store.setFilters({ keyword })
    loadProperties(1)
  }

  const handlePriceTabChange = (key) => {
    setPriceTab(key)
    const priceTypeMap = { '': '', rent: 'RENT', sale: 'SALE' }
    store.setFilters({ priceType: priceTypeMap[key] })
    refreshProperties()
  }

  const handleBedroomClick = (val) => {
    setBedrooms(val)
    store.setFilters({ bedrooms: val })
    refreshProperties()
  }

  const handleOpenFilter = () => {
    setLocalDistrict(filters.district || '')
    setLocalMinPrice('')
    setLocalMaxPrice('')
    setLocalSource(filters.source || '')
    setLocalSort(filters.sort || '')
    setFilterVisible(true)
  }

  const handleApplyFilter = () => {
    store.setFilters({
      district: localDistrict,
      minPrice: localMinPrice,
      maxPrice: localMaxPrice,
      source: localSource,
      sort: localSort,
    })
    setFilterVisible(false)
    refreshProperties()
  }

  const handleClearFilter = () => {
    setLocalDistrict('')
    setLocalMinPrice('')
    setLocalMaxPrice('')
    setLocalSource('')
    setLocalSort('')
    store.setFilters({
      district: '', minPrice: '', maxPrice: '', source: '', sort: '',
    })
    setFilterVisible(false)
    refreshProperties()
  }

  return (
    <div className="search-page">
      {/* Search Bar */}
      <SearchBar
        value={keyword}
        onChange={setKeyword}
        placeholder="输入城市、区域或房产名称"
        onSearch={handleSearch}
        onClear={() => { setKeyword(''); store.setFilters({ keyword: '' }); loadProperties(1) }}
      />

      {/* Quick Filters */}
      <div className="quick-filters">
        <Tabs activeKey={priceTab} onChange={handlePriceTabChange}>
          <Tabs.Tab title="全部" key="" />
          <Tabs.Tab title="出租" key="rent" />
          <Tabs.Tab title="出售" key="sale" />
        </Tabs>
        <div className="bedroom-chips">
          {BEDROOM_OPTIONS.map((item) => (
            <Tag
              key={item.value}
              color={bedrooms === item.value ? 'danger' : 'default'}
              fill={bedrooms === item.value ? 'solid' : 'outline'}
              style={{ cursor: 'pointer', padding: '4px 10px' }}
              onClick={() => handleBedroomClick(item.value)}
            >
              {item.label}
            </Tag>
          ))}
        </div>
      </div>

      {/* Result Bar */}
      <div className="result-bar">
        <span className="result-count">找到 {totalCount} 套房源</span>
        <Button size="small" color="primary" fill="none" onClick={handleOpenFilter}>
          筛选
        </Button>
      </div>

      {/* Property List */}
      <PullToRefresh onRefresh={refreshProperties}>
        {loading && properties.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <DotLoading color="primary" />
            <div style={{ color: '#999', fontSize: 13, marginTop: 8 }}>加载中...</div>
          </div>
        ) : properties.length === 0 ? (
          <Empty description="未找到匹配房源" />
        ) : (
          <>
            <div className="property-list">
              {properties.map((p) => (
                <PropertyCard key={p.id} property={p} />
              ))}
            </div>
            <InfiniteScroll loadMore={loadMore} hasMore={!finished} />
          </>
        )}
      </PullToRefresh>

      {/* Filter Popup */}
      <Popup
        visible={filterVisible}
        onMaskClick={() => setFilterVisible(false)}
        bodyStyle={{ height: '70vh', borderTopLeftRadius: 12, borderTopRightRadius: 12 }}
      >
        <div className="filter-content">
          {/* District */}
          {districts.length > 0 && (
            <div className="filter-group">
              <div className="filter-label">区域</div>
              <div className="filter-tags">
                <Tag
                  color={localDistrict === '' ? 'primary' : 'default'}
                  fill={localDistrict === '' ? 'solid' : 'outline'}
                  style={{ cursor: 'pointer', padding: '4px 12px', marginBottom: 4 }}
                  onClick={() => setLocalDistrict('')}
                >全部</Tag>
                {districts.map((d) => (
                  <Tag
                    key={d.id || d.district || d.name}
                    color={localDistrict === (d.district || d.name) ? 'primary' : 'default'}
                    fill={localDistrict === (d.district || d.name) ? 'solid' : 'outline'}
                    style={{ cursor: 'pointer', padding: '4px 12px', marginBottom: 4 }}
                    onClick={() => setLocalDistrict(d.district || d.name)}
                  >{d.district || d.name}</Tag>
                ))}
              </div>
            </div>
          )}

          {/* Price Range */}
          <div className="filter-group">
            <div className="filter-label">价格区间（万泰铢/月）</div>
            <div className="price-inputs">
              <Input placeholder="最低价" value={localMinPrice} onChange={setLocalMinPrice} type="number" />
              <span style={{ color: '#ccc' }}>—</span>
              <Input placeholder="最高价" value={localMaxPrice} onChange={setLocalMaxPrice} type="number" />
            </div>
          </div>

          {/* Source */}
          <div className="filter-group">
            <div className="filter-label">来源</div>
            <div className="filter-tags">
              {SOURCE_OPTIONS.map((opt) => (
                <Tag
                  key={opt.value}
                  color={localSource === opt.value ? 'primary' : 'default'}
                  fill={localSource === opt.value ? 'solid' : 'outline'}
                  style={{ cursor: 'pointer', padding: '4px 12px', marginBottom: 4 }}
                  onClick={() => setLocalSource(opt.value)}
                >{opt.label}</Tag>
              ))}
            </div>
          </div>

          {/* Sort */}
          <div className="filter-group">
            <div className="filter-label">排序方式</div>
            <div className="filter-tags">
              {SORT_OPTIONS.map((opt) => (
                <Tag
                  key={opt.value}
                  color={localSort === opt.value ? 'primary' : 'default'}
                  fill={localSort === opt.value ? 'solid' : 'outline'}
                  style={{ cursor: 'pointer', padding: '4px 12px', marginBottom: 4 }}
                  onClick={() => setLocalSort(opt.value)}
                >{opt.label}</Tag>
              ))}
            </div>
          </div>

          <Button block color="primary" size="large" style={{ marginTop: 16 }} onClick={handleApplyFilter}>
            应用筛选
          </Button>
          <Button block fill="none" size="small" style={{ marginTop: 8 }} onClick={handleClearFilter}>
            清除筛选
          </Button>
        </div>
      </Popup>
    </div>
  )
}
