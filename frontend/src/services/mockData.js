// 清迈房产 — 中文模拟数据（用于离线开发）
// 房产区域参考坐标

const districts = [
  { id: 1, name: '古城', nameEn: 'Old City', count: 128, lat: 18.7883, lng: 98.9853 },
  { id: 2, name: '宁曼路', nameEn: 'Nimman', count: 95, lat: 18.8000, lng: 98.9680 },
  { id: 3, name: '长康路', nameEn: 'Chang Klan', count: 73, lat: 18.7800, lng: 98.9980 },
  { id: 4, name: '杭东', nameEn: 'Hang Dong', count: 156, lat: 18.6870, lng: 98.9190 },
  { id: 5, name: '讪赛', nameEn: 'San Sai', count: 88, lat: 18.8500, lng: 99.0500 },
  { id: 6, name: '湄林', nameEn: 'Mae Rim', count: 62, lat: 18.9000, lng: 98.9500 },
  { id: 7, name: '山甘烹', nameEn: 'San Kamphaeng', count: 45, lat: 18.7400, lng: 99.1200 },
  { id: 8, name: '沙拉丕', nameEn: 'Saraphi', count: 38, lat: 18.7000, lng: 99.0100 },
  { id: 9, name: '东岸', nameEn: 'Fa Ham', count: 52, lat: 18.8200, lng: 99.0200 },
  { id: 10, name: '清迈大学附近', nameEn: 'CMU Area', count: 110, lat: 18.8050, lng: 98.9550 },
]

const thaiNames = [
  'Supalai Monte @Nimman',
  'The Astra Condo',
  'D Condo Sign',
  'Punna Oasis Town',
  'Hillside Plaza Condotel',
  'The Punna Classic',
  'Burasiri San Sai',
  'Hypo Central Suites',
  'The Shine Nimman',
  'The Unique at Nimman',
  'Supalai Oasis',
  'Green Hill Place',
  'Baan Tawai Wood',
  'The Bliss Condo',
  'Laguna Homes Hang Dong',
]

function generateMockProperties(count = 30) {
  const properties = []
  const priceTypes = ['rent', 'sale']
  const propertyTypes = ['condo', 'house', 'townhouse', 'apartment']

  for (let i = 1; i <= count; i++) {
    const district = districts[Math.floor(Math.random() * districts.length)]
    const isRent = Math.random() > 0.4
    const bedrooms = [1, 1, 2, 2, 2, 3, 3, 4][Math.floor(Math.random() * 8)]
    const bathrooms = Math.min(bedrooms + (Math.random() > 0.5 ? 1 : 0), 5)

    properties.push({
      id: i,
      title: `${district.name} — ${thaiNames[i % thaiNames.length]}`,
      description: `${bedrooms}卧${bathrooms}卫，精装修，位于${district.name}核心区域，周边配套齐全，交通便利。步行可达7-11、大型超市和公交站。`,
      price_rent: isRent ? [5000, 8000, 10000, 12000, 15000, 18000, 22000, 28000, 35000, 45000][Math.floor(Math.random() * 10)] : null,
      price_sale: !isRent ? [1500000, 2000000, 2800000, 3500000, 4500000, 5500000, 7000000, 8900000, 12000000, 18000000][Math.floor(Math.random() * 10)] : null,
      currency: 'THB',
      price_type: isRent ? 'rent' : 'sale',
      bedrooms,
      bathrooms,
      area_sqm: [25, 30, 35, 40, 45, 50, 60, 75, 90, 110, 140, 180][Math.floor(Math.random() * 12)],
      floor: Math.floor(Math.random() * 15) + 1,
      total_floors: Math.floor(Math.random() * 15) + 5,
      furnished: Math.random() > 0.2,
      property_type: propertyTypes[Math.floor(Math.random() * propertyTypes.length)],
      address: `${district.name}区，清迈`,
      district: district.name,
      sub_district: ['Pa Tan', 'Suthep', 'Chang Phueak', 'Hai Ya', 'Pa Daet'][Math.floor(Math.random() * 5)],
      lat: district.lat + (Math.random() - 0.5) * 0.03,
      lng: district.lng + (Math.random() - 0.5) * 0.03,
      source: ['ddproperty', 'hipflat', 'fazwaz'][Math.floor(Math.random() * 3)],
      source_url: '#',
      source_id: `mock_${i}`,
      images: [
        `https://picsum.photos/seed/cm${i}a/800/500`,
        `https://picsum.photos/seed/cm${i}b/800/500`,
        `https://picsum.photos/seed/cm${i}c/800/500`,
      ],
      is_active: true,
      posted_date: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
      scraped_at: new Date().toISOString(),
      // 计算字段
      price_per_sqm: isRent
        ? Math.round([5000, 8000, 10000, 12000, 15000, 18000, 22000, 28000, 35000, 45000][Math.floor(Math.random() * 10)] / [25, 30, 35, 40, 45, 50, 60, 75, 90, 110, 140, 180][Math.floor(Math.random() * 12)])
        : Math.round([1500000, 2000000, 2800000, 3500000, 4500000, 5500000, 7000000, 8900000, 12000000, 18000000][Math.floor(Math.random() * 10)] / [25, 30, 35, 40, 45, 50, 60, 75, 90, 110, 140, 180][Math.floor(Math.random() * 12)]),
      source_label: { ddproperty: 'DD Property', hipflat: 'Hipflat', fazwaz: 'FazWaz' }[{ ddproperty: 'ddproperty', hipflat: 'hipflat', fazwaz: 'fazwaz' }[['ddproperty', 'hipflat', 'fazwaz'][Math.floor(Math.random() * 3)]]],
    })
  }
  return properties
}

export const mockProperties = generateMockProperties(30)
export { districts }
