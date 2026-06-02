import React, { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  SearchBar, Tabs, Tag, Button,
  PullToRefresh, InfiniteScroll, Empty, DotLoading,
  Popup, Input,
} from 'antd-mobile'
import usePropertyStore from '../stores/propertyStore'
import PropertyCard from '../components/PropertyCard'
import { useT } from '../i18n'

export default function SearchPage() {
  const t = useT()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const store = usePropertyStore()
  const { properties, totalCount, loading, finished, districts, filters } = store

  // Read filter state from URL params (persists across navigation)
  const [keyword, setKeyword] = useState(searchParams.get('keyword') || filters.keyword || '')
  const [priceTab, setPriceTab] = useState(searchParams.get('priceType') || '')
  const [bedrooms, setBedrooms] = useState(searchParams.get('bedrooms') || '')
  const [filterVisible, setFilterVisible] = useState(false)

  const BEDROOM_OPTIONS = [
    { label: t('all'), value: '' },
    { label: '1' + t('bedroom'), value: '1' },
    { label: '2' + t('bedroom'), value: '2' },
    { label: '3' + t('bedroom'), value: '3' },
    { label: '4' + t('bedroom'), value: '4' },
    { label: '5' + t('bedroom') + '+', value: '5' },
  ]

  const SOURCE_OPTIONS = [
    { label: t('allSources'), value: '' },
    { label: 'HipFlat', value: 'hipflat' },
    { label: 'FazWaz', value: 'fazwaz' },
    { label: 'DDProperty', value: 'ddproperty' },
  ]

  const SORT_OPTIONS = [
    { label: t('defaultSort'), value: '' },
    { label: t('priceAsc'), value: 'price_asc' },
    { label: t('priceDesc'), value: 'price_desc' },
    { label: t('areaDesc'), value: 'area_desc' },
    { label: t('newest'), value: 'newest' },
  ]

  // Local filter states (initialized from URL params)
  const [localDistrict, setLocalDistrict] = useState(searchParams.get('district') || '')
  const [localMinPrice, setLocalMinPrice] = useState(searchParams.get('minPrice') || '')
  const [localMaxPrice, setLocalMaxPrice] = useState(searchParams.get('maxPrice') || '')
  const [localSource, setLocalSource] = useState(searchParams.get('source') || '')
  const [localSort, setLocalSort] = useState(searchParams.get('sort') || '')

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
    const newParams = new URLSearchParams(searchParams)
    if (keyword) newParams.set('keyword', keyword)
    else newParams.delete('keyword')
    setSearchParams(newParams, { replace: true })
    store.setFilters({ keyword })
    loadProperties(1)
  }

  const handlePriceTabChange = (key) => {
    setPriceTab(key)
    const priceTypeMap = { '': '', rent: 'RENT', sale: 'SALE' }
    const newParams = new URLSearchParams(searchParams)
    if (key) newParams.set('priceType', key)
    else newParams.delete('priceType')
    setSearchParams(newParams, { replace: true })
    store.setFilters({ priceType: priceTypeMap[key] })
    refreshProperties()
  }

  const handleBedroomClick = (val) => {
    setBedrooms(val)
    const newParams = new URLSearchParams(searchParams)
    if (val) newParams.set('bedrooms', val)
    else newParams.delete('bedrooms')
    setSearchParams(newParams, { replace: true })
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
    const newParams = new URLSearchParams(searchParams)
    const filterFields = { district: localDistrict, minPrice: localMinPrice, maxPrice: localMaxPrice, source: localSource, sort: localSort }
    Object.entries(filterFields).forEach(([k, v]) => {
      if (v) newParams.set(k, v)
      else newParams.delete(k)
    })
    setSearchParams(newParams, { replace: true })
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
    // Clear URL params
    const newParams = new URLSearchParams(searchParams)
    ;['district', 'minPrice', 'maxPrice', 'source', 'sort'].forEach(k => newParams.delete(k))
    setSearchParams(newParams, { replace: true })
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
        placeholder={t('searchPlaceholder')}
        onSearch={handleSearch}
        onClear={() => { setKeyword(''); store.setFilters({ keyword: '' }); loadProperties(1) }}
      />

      {/* Quick Filters */}
      <div className="quick-filters">
        <Tabs activeKey={priceTab} onChange={handlePriceTabChange}>
          <Tabs.Tab title={t('all')} key="" />
          <Tabs.Tab title={t('rent')} key="rent" />
          <Tabs.Tab title={t('sale')} key="sale" />
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
        <span className="result-count">{t('findResults')} {totalCount} {t('results')}</span>
        <Button size="small" color="primary" fill="none" onClick={handleOpenFilter}>
          {t('filter')}
        </Button>
      </div>

      {/* Property List */}
      <PullToRefresh onRefresh={refreshProperties}>
        {loading && properties.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <DotLoading color="primary" />
            <div style={{ color: '#999', fontSize: 13, marginTop: 8 }}>{t('loading')}</div>
          </div>
        ) : properties.length === 0 ? (
          <Empty description={t('noResults')} />
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
              <div className="filter-label">{t('selectDistrict')}</div>
              <div className="filter-tags">
                <Tag
                  color={localDistrict === '' ? 'primary' : 'default'}
                  fill={localDistrict === '' ? 'solid' : 'outline'}
                  style={{ cursor: 'pointer', padding: '4px 12px', marginBottom: 4 }}
                  onClick={() => setLocalDistrict('')}
                >{t('all')}</Tag>
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
            <div className="filter-label">{t('priceRange')}</div>
            <div className="price-inputs">
              <Input placeholder={t('minPrice')} value={localMinPrice} onChange={setLocalMinPrice} type="number" />
              <span style={{ color: '#ccc' }}>—</span>
              <Input placeholder={t('maxPrice')} value={localMaxPrice} onChange={setLocalMaxPrice} type="number" />
            </div>
          </div>

          {/* Source */}
          <div className="filter-group">
            <div className="filter-label">{t('source')}</div>
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
            <div className="filter-label">{t('sortBy')}</div>
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
            {t('applyFilter')}
          </Button>
          <Button block fill="none" size="small" style={{ marginTop: 8 }} onClick={handleClearFilter}>
            {t('clearFilter')}
          </Button>
        </div>
      </Popup>
    </div>
  )
}
