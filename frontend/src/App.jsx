import { useEffect, useMemo, useState } from 'react'
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import { ArrowDownRight, ArrowRight, ArrowUpRight, BadgeCheck, Bean, Clock3, Coffee, CreditCard, History, Home, LocateFixed, LogOut, MapPin, Menu, QrCode, Search, ShieldCheck, Sparkles, X } from 'lucide-react'
import { Circle, CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { api, getErrorMessage } from './api'
import { translate as t } from './i18n'

const defaultCenter = [38.4237, 27.1428]
const plans = [
  { key: 'STARTER', title: 'Starter', price: '89,99', credits: '10', label: 'Günlük kahve molaları için' },
  { key: 'PREMIUM', title: 'Premium', price: '149,99', credits: '20', label: 'Kahve senin ritminse', featured: true },
  { key: 'UNLIMITED', title: 'Unlimited', price: '249,99', credits: '∞', label: 'Kahveye sınır koyma' },
]

function useCopy() {
  const [language, setLanguage] = useState(localStorage.getItem('kahvecell.language') || 'tr')
  const toggleLanguage = () => setLanguage((current) => {
    const next = current === 'tr' ? 'en' : 'tr'
    localStorage.setItem('kahvecell.language', next)
    return next
  })
  return { language, text: (key) => t(language, key), toggleLanguage }
}

function AppFrame({ children, text, toggleLanguage }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const authenticated = Boolean(localStorage.getItem('kahvecell.accessToken'))
  const navItems = [
    { to: '/home', label: text('navHome'), icon: Home, end: true },
    { to: '/subscription', label: text('navSubscription'), icon: Coffee },
    { to: '/history', label: text('navHistory'), icon: History },
  ]
  const logout = () => {
    localStorage.removeItem('kahvecell.accessToken')
    localStorage.removeItem('kahvecell.refreshToken')
    window.location.assign('/')
  }
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <Link className="brand" to="/home" onClick={() => setMobileOpen(false)}>
          <span className="brand-mark"><Bean size={21} fill="currentColor" /></span>
          <span>Kahve<span className="brand-accent">Cell</span><small>ŞEHRİN KAHVE AĞI</small></span>
        </Link>
        <div className="nav-caption">MENÜ</div>
        <nav className="side-nav">
          {navItems.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Icon size={18} /><span>{label}</span>{to === '/' && <span className="nav-dot" />}</NavLink>)}
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card"><span className="help-icon"><Sparkles size={16} /></span><strong>Günün güzel geçsin.</strong><p>İyi kahvenin bahanesi olmaz.</p></div>
          {authenticated ? <button className="nav-link logout-button" onClick={logout}><LogOut size={18} /><span>{text('signOut')}</span></button> : <NavLink className="nav-link" to="/login"><ShieldCheck size={18} /><span>{text('signIn')}</span></NavLink>}
        </div>
        <button className="language-switch" onClick={toggleLanguage}><span>◎</span> Türkçe <span className="language-current">{text('lang')}</span></button>
      </aside>
      {mobileOpen && <button className="mobile-scrim" aria-label="Menüyü kapat" onClick={() => setMobileOpen(false)} />}
      <main className="main-area">
        <header className="topbar"><button className="icon-button mobile-menu-button" aria-label="Menüyü aç" onClick={() => setMobileOpen(true)}><Menu size={20} /></button><div className="breadcrumb"><span>KahveCell</span><span className="breadcrumb-separator">/</span><span>İzmir</span></div><div className="topbar-right"><span className="city-pill"><MapPin size={14} /> İzmir, Türkiye</span><button className="avatar" title="Profil">E</button></div></header>
        <div className="page-content">{children}</div>
        <footer className="footer"><span>© 2026 KahveCell</span><span>Bir kahve molası kadar yakın.</span><span className="footer-live"><i /> Servis aktif</span></footer>
      </main>
    </div>
  )
}

function useLoad(load, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: '' })
  useEffect(() => {
    let alive = true
    setState((current) => ({ ...current, loading: true, error: '' }))
    load().then((data) => alive && setState({ data, loading: false, error: '' })).catch((error) => alive && setState({ data: null, loading: false, error: getErrorMessage(error) }))
    return () => { alive = false }
  }, deps)
  return state
}

function MapView({ shops, center, text }) {
  function Recenter({ position }) {
    const map = useMap()
    useEffect(() => { map.setView(position, 13) }, [map, position])
    return null
  }
  return <div className="map-frame"><MapContainer center={center} zoom={12} scrollWheelZoom={false}>
    <Recenter position={center} /><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <Circle center={center} radius={650} pathOptions={{ color: '#ffc72c', fillColor: '#ffc72c', fillOpacity: 0.08, weight: 1 }} />
    {shops.map((shop) => <CircleMarker key={shop.id} center={[shop.latitude, shop.longitude]} radius={8} pathOptions={{ color: '#ffffff', weight: 3, fillColor: '#ffd12e', fillOpacity: 1 }}><Popup><div className="map-popup"><strong>{shop.name}</strong><span>{shop.distance_km != null ? `${shop.distance_km} km` : shop.address}</span><Link to={`/shops/${shop.id}`}>{text('details')} <ArrowRight size={13} /></Link></div></Popup></CircleMarker>)}
  </MapContainer><div className="map-overlay"><span className="map-live-dot" /> {text('mapNote')}</div></div>
}

function ShopCard({ shop, text }) {
  return <Link to={`/shops/${shop.id}`} className="shop-card"><div className="shop-card-art"><div className="cup-illustration"><Coffee size={29} /></div><span className="open-badge"><i /> {text('open')}</span><span className="shop-distance">{shop.distance_km != null ? `${shop.distance_km} km` : 'İzmir'}</span></div><div className="shop-card-body"><div className="shop-card-title"><h3>{shop.name}</h3><span className="rating">★ 4.8</span></div><p><MapPin size={13} /> {shop.address}</p><div className="shop-card-bottom"><span><Clock3 size={13} /> {shop.opening_hours || '08:00–22:00'}</span><span className="card-link">{text('details')} <ArrowRight size={14} /></span></div></div></Link>
}

function HomePage({ text }) {
  const [query, setQuery] = useState('')
  const [position, setPosition] = useState(defaultCenter)
  const [locationMessage, setLocationMessage] = useState('')
  const { data: shopData, loading, error } = useLoad(async () => {
    const params = { latitude: position[0], longitude: position[1] }
    if (query.trim()) params.q = query.trim()
    const response = await api.get('/shops', { params })
    return response.data
  }, [query, position])
  const shops = shopData ?? []
  const locate = () => {
    if (!navigator.geolocation) { setLocationMessage('Bu tarayıcı konum erişimini desteklemiyor.'); return }
    navigator.geolocation.getCurrentPosition(({ coords }) => { setPosition([coords.latitude, coords.longitude]); setLocationMessage('Konumun kullanılıyor.') }, () => setLocationMessage('Konum alınamadı; İzmir merkezi gösteriliyor.'), { enableHighAccuracy: true, timeout: 7000 })
  }
  const mapCenter = shops.length ? [shops[0].latitude, shops[0].longitude] : position
  return <>
    <section className="hero-panel"><div className="hero-copy"><span className="eyebrow"><span /> {text('eyebrow')}</span><h1>{text('heroTitle').split('\n').map((line, index) => <span key={line}>{index === 1 ? <>{line.split(' ')[0]} <em>{line.split(' ').slice(1).join(' ')}</em></> : line}<br /></span>)}</h1><p>{text('heroBody')}</p><div className="hero-actions"><Link className="button button-yellow" to="/subscription">Paketleri keşfet <ArrowRight size={16} /></Link><button className="button button-ghost" onClick={locate}><LocateFixed size={16} /> {text('locate')}</button></div>{locationMessage && <span className="inline-note">{locationMessage}</span>}<div className="hero-proof"><div className="proof-avatars"><span>A</span><span>M</span><span>+</span></div><span><strong>İzmir’de kahve keşfi</strong><small>Favori semtinde, favori fincanın.</small></span></div></div><div className="hero-art"><div className="sun-glow" /><div className="hero-orbit orbit-one" /><div className="hero-orbit orbit-two" /><div className="hero-coffee"><div className="coffee-steam steam-one" /><div className="coffee-steam steam-two" /><div className="cup-top"><span /></div><div className="cup-body"><span>KC</span></div><div className="cup-saucer" /></div><span className="floating-label label-top"><Sparkles size={14} /> Her gün, iyi kahve</span><span className="floating-label label-bottom"><MapPin size={14} /> 5 seçkin durak</span><div className="hero-art-caption">İyi hisset. Kahveni seç.</div></div><div className="hero-watermark">K</div></section>
    <section className="section-block"><div className="section-heading"><div><span className="section-kicker">ŞEHRİN KAHVE HARİTASI</span><h2>{text('nearby')}</h2><p>İzmir’in güzel köşelerinde, sana yakın bir mola var.</p></div><button className="text-button" onClick={locate}><LocateFixed size={15} /> {text('locate')}</button></div>
      <div className="explore-grid"><div className="shop-list-panel"><div className="search-box"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={text('search')} aria-label={text('search')} />{query && <button onClick={() => setQuery('')} aria-label="Aramayı temizle"><X size={15} /></button>}</div>{error && <div className="notice notice-error">{error}</div>}{loading ? <div className="loading-state">{text('loading')}</div> : shops.length ? <div className="shop-list">{shops.map((shop) => <ShopCard key={shop.id} shop={shop} text={text} />)}</div> : <div className="empty-state"><Coffee size={23} /><strong>{text('empty')}</strong><span>Aramanı değiştirmeyi deneyebilirsin.</span></div>}</div><MapView shops={shops} center={mapCenter} text={text} /></div>
    </section>
    <section className="bottom-cta"><div className="cta-icon"><Coffee size={25} /></div><div><span className="section-kicker">KAHVE MOLASI SANA ÖZEL</span><h2>İyi kahve, güzel bir alışkanlık.</h2><p>Sana uyan paketi seç, şehrin kahve duraklarını keşfet.</p></div><Link className="button button-dark" to="/subscription">Paketleri gör <ArrowRight size={16} /></Link></section>
  </>
}

function AuthPage({ text }) {
  const navigate = useNavigate()
  const [step, setStep] = useState('phone')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('1234')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submitPhone = async (event) => {
    event.preventDefault(); setBusy(true); setError('')
    try { await api.post('/auth/register', { phone_number: phone }); setStep('otp') } catch (failure) { setError(getErrorMessage(failure)) } finally { setBusy(false) }
  }
  const submitOtp = async (event) => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const { data } = await api.post('/auth/verify-otp', { phone_number: phone, code: otp })
      localStorage.setItem('kahvecell.accessToken', data.access_token)
      localStorage.setItem('kahvecell.refreshToken', data.refresh_token)
      setStep('profile')
    } catch (failure) { setError(getErrorMessage(failure)) } finally { setBusy(false) }
  }
  const submitProfile = async (event) => {
    event.preventDefault(); setBusy(true); setError('')
    try { await api.put('/auth/profile', { full_name: fullName, email: null, preferences: {} }); navigate('/home') } catch (failure) { setError(getErrorMessage(failure)) } finally { setBusy(false) }
  }
  return <div className="auth-layout"><div className="auth-visual"><Link to="/home" className="brand brand-light"><span className="brand-mark"><Bean size={21} fill="currentColor" /></span><span>Kahve<span className="brand-accent">Cell</span></span></Link><div><span className="eyebrow"><span /> KAHVENİN GÜZEL HALİ</span><h1>Her güzel gün<br />bir kahveyle<br /><em>başlayabilir.</em></h1><p>İzmir’in sevilen kahvecileri, cebinde bir abonelikle.</p></div><div className="auth-orbit"><Coffee size={94} strokeWidth={1} /></div><span className="auth-footnote">Kahve molan, şehrinle buluşsun.</span></div><div className="auth-form-wrap"><form className="auth-form" onSubmit={step === 'phone' ? submitPhone : step === 'otp' ? submitOtp : submitProfile}><span className="form-step">0{step === 'phone' ? 1 : step === 'otp' ? 2 : 3} <span>/ 03</span></span><h2>{step === 'phone' ? text('loginTitle') : step === 'otp' ? 'Sana bir kod gönderdik.' : text('complete')}</h2><p>{step === 'phone' ? 'Telefon numaranla güvenle devam et.' : step === 'otp' ? `${phone} numarasına gönderilen kodu gir. Demo kodu: 1234` : 'Kahve deneyimini sana göre kişiselleştirelim.'}</p>{error && <div className="notice notice-error">{error}</div>}{step === 'phone' && <label>{text('phone')}<input autoFocus value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="05__ ___ __ __" inputMode="tel" required pattern="05[0-9]{9}" /></label>}{step === 'otp' && <label>{text('otp')}<input autoFocus value={otp} onChange={(event) => setOtp(event.target.value)} maxLength={4} inputMode="numeric" required /></label>}{step === 'profile' && <label>{text('fullName')}<input autoFocus value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Adın ve soyadın" minLength={2} required /></label>}<button className="button button-yellow button-wide" disabled={busy}>{busy ? text('loading') : step === 'phone' ? text('sendOtp') : step === 'otp' ? text('verify') : text('complete')} <ArrowRight size={16} /></button>{step !== 'phone' && <button type="button" className="back-link" onClick={() => { setError(''); setStep(step === 'profile' ? 'phone' : 'phone') }}>{text('back')}</button>}<span className="secure-note"><ShieldCheck size={14} /> Bilgilerin güvenle saklanır.</span></form></div></div>
}

function ShopPage({ text }) {
  const { shopId } = useParams()
  const { data: shop, loading, error } = useLoad(async () => (await api.get(`/shops/${shopId}`)).data, [shopId])
  if (loading) return <div className="loading-state page-loading">{text('loading')}</div>
  if (error || !shop) return <div className="notice notice-error">{error || text('empty')}</div>
  return <><Link className="back-link inline-back" to="/home">← {text('back')}</Link><section className="shop-detail-hero"><div className="detail-photo"><div className="detail-cup"><Coffee size={72} /></div><span className="open-badge"><i /> {text('open')}</span><span className="photo-tag">KAHVECELL SEÇKİSİ</span></div><div className="detail-copy"><span className="section-kicker">İZMİR · KAHVE DURAĞI</span><h1>{shop.name}</h1><p><MapPin size={16} /> {shop.address}</p><p><Clock3 size={16} /> {shop.opening_hours || '08:00–22:00'}</p><div className="detail-rating"><span>★ 4.8</span><span>•</span><span>Şehrin sevilen noktalarından</span></div><a className="button button-yellow" href="#menu">Menüye göz at <ArrowDownRight size={16} /></a></div></section><section id="menu" className="section-block"><div className="section-heading"><div><span className="section-kicker">ÖZENLE HAZIRLANDI</span><h2>Menü</h2><p>Bugünkü kahve molanı seç.</p></div></div><div className="product-grid">{shop.products?.map((product, index) => <article className="product-card" key={product.id}><div className={`product-art product-art-${index % 4}`}><Coffee size={30} /><span>0{index + 1}</span></div><div className="product-info"><div><h3>{product.name}</h3><p>{product.description || 'Özenle hazırlanmış, taze kahve.'}</p></div><strong>{product.base_price.toLocaleString('tr-TR')} ₺</strong></div><Link className="button button-dark button-wide" to={`/shops/${shop.id}/order?product=${product.id}`}>{text('order')} <ArrowRight size={15} /></Link></article>)}</div></section></>
}

function OrderPage({ text }) {
  const { shopId } = useParams()
  const navigate = useNavigate()
  const productId = new URLSearchParams(window.location.search).get('product')
  const { data: shop, loading, error } = useLoad(async () => (await api.get(`/shops/${shopId}`)).data, [shopId])
  const [selection, setSelection] = useState({ size: 'M', sugar: 0, milk: 'regular', extra_shots: 0 })
  const [requestError, setRequestError] = useState('')
  const [busy, setBusy] = useState(false)
  const product = shop?.products?.find((item) => String(item.id) === productId)
  const placeOrder = async (event) => {
    event.preventDefault(); setBusy(true); setRequestError('')
    try { const { data } = await api.post('/orders', { shop_id: Number(shopId), product_id: Number(productId), ...selection }); navigate(`/qr/${data.id}`, { state: { order: data } }) } catch (failure) { setRequestError(getErrorMessage(failure)) } finally { setBusy(false) }
  }
  if (loading) return <div className="loading-state page-loading">{text('loading')}</div>
  if (error || !shop || !product) return <div className="notice notice-error">{error || 'Ürün bulunamadı. Dükkân menüsünden seçim yap.'}<p><Link to={`/shops/${shopId}`}>Dükkân menüsüne dön</Link></p></div>
  return <div className="order-layout"><section className="order-main"><Link className="back-link inline-back" to={`/shops/${shop.id}`}>← {shop.name}</Link><span className="section-kicker">SİPARİŞİNİ KİŞİSELLEŞTİR</span><h1>{text('order')}</h1><p className="muted">Tam istediğin gibi bir fincan hazırlayalım.</p><form className="order-form" onSubmit={placeOrder}><div className="order-product"><div className="order-product-icon"><Coffee size={25} /></div><div><strong>{product.name}</strong><span>{shop.name}</span></div><b>{product.base_price.toLocaleString('tr-TR')} ₺</b></div><fieldset><legend>{text('size')}</legend><div className="option-row">{['S', 'M', 'L'].map((size) => <button type="button" key={size} className={`size-option ${selection.size === size ? 'selected' : ''}`} onClick={() => setSelection({ ...selection, size })}><strong>{size}</strong><small>{size === 'S' ? 'Küçük' : size === 'M' ? 'Orta' : 'Büyük'}</small></button>)}</div></fieldset><label>{text('sugar')}<select value={selection.sugar} onChange={(event) => setSelection({ ...selection, sugar: Number(event.target.value) })}>{[0, 1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n === 0 ? 'Şekersiz' : `${n} küp`}</option>)}</select></label><label>{text('milk')}<select value={selection.milk} onChange={(event) => setSelection({ ...selection, milk: event.target.value })}><option value="regular">Normal süt</option><option value="oat">Yulaf sütü</option><option value="almond">Badem sütü</option><option value="lactose-free">Laktozsuz süt</option><option value="none">Sütsüz</option></select></label><label>{text('shots')}<select value={selection.extra_shots} onChange={(event) => setSelection({ ...selection, extra_shots: Number(event.target.value) })}><option value="0">Ek shot yok</option><option value="1">+1 shot</option><option value="2">+2 shot</option><option value="3">+3 shot</option></select></label>{requestError && <div className="notice notice-error">{requestError}</div>}<button className="button button-yellow button-wide" disabled={busy}>{busy ? text('loading') : text('placeOrder')} <ArrowRight size={16} /></button></form></section><aside className="order-aside"><span className="aside-icon"><Bean size={20} /></span><span className="section-kicker">KAHVECELL ABONELİĞİ</span><h3>Bir hakkınla, güzel bir mola.</h3><p>Abonelik hakkın sipariş onaylandığında güncellenir.</p><div className="aside-divider" /><span className="secure-note"><ShieldCheck size={15} /> Güvenli sipariş</span></aside></div>
}

function QrPage({ text }) {
  const { orderId } = useParams()
  const { state } = useLocation()
  const { data: fetchedOrder, loading, error } = useLoad(async () => (await api.get(`/orders/${orderId}`)).data, [orderId])
  const order = state?.order || fetchedOrder
  if (loading && !order) return <div className="loading-state page-loading">{text('loading')}</div>
  if (error && !order) return <div className="notice notice-error">{error}</div>
  if (!order) return null
  return <div className="qr-page"><Link className="back-link inline-back" to="/history">← {text('myOrders')}</Link><div className="qr-card"><div className="qr-heading"><span className="qr-status"><BadgeCheck size={15} /> Sipariş alındı</span><span className="order-number">#{String(order.id).padStart(4, '0')}</span></div><div className="qr-content"><div className="qr-image-wrap"><img src={order.qr_image} alt="Sipariş doğrulama QR kodu" /></div><span className="qr-icon"><QrCode size={18} /></span><h1>{text('qrTitle')}</h1><p>{text('qrBody')}</p><div className="qr-order-line"><span>{order.shop_name}</span><span>·</span><span>{order.items?.[0]?.product_name}</span></div><div className="qr-safety"><ShieldCheck size={15} /> İmzalı ve doğrulanabilir kod</div></div><div className="qr-card-footer"><span>SİPARİŞ DURUMU</span><strong>{String(order.status).replaceAll('_', ' ')}</strong></div></div><Link className="button button-dark" to="/history">Siparişlerime git <ArrowRight size={16} /></Link></div>
}

function HistoryPage({ text }) {
  const { data: orderData, loading, error } = useLoad(async () => (await api.get('/orders/history')).data, [])
  const orders = orderData ?? []
  return <section className="section-block page-section"><div className="section-heading"><div><span className="section-kicker">KAHVE ANILARIN</span><h1>{text('myOrders')}</h1><p>Önceki siparişlerini ve durumlarını burada görebilirsin.</p></div></div>{error && <div className="notice notice-error">{error}</div>}{loading ? <div className="loading-state">{text('loading')}</div> : orders.length ? <div className="history-list">{orders.map((order) => <Link className="history-card" key={order.id} to={`/qr/${order.id}`}><div className="history-icon"><Coffee size={19} /></div><div className="history-detail"><strong>{order.items?.[0]?.product_name || 'Kahve siparişi'}</strong><span>{order.shop_name} · {new Date(order.created_at).toLocaleString('tr-TR')}</span></div><span className="history-status">{String(order.status).replaceAll('_', ' ')}</span><ArrowRight size={16} /></Link>)}</div> : <div className="empty-state panel-empty"><History size={25} /><strong>{text('noOrders')}</strong><Link to="/home">Kahvecileri keşfet <ArrowRight size={14} /></Link></div>}</section>
}

function SubscriptionPage({ text }) {
  const [active, setActive] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [card, setCard] = useState({ card_holder: '', card_number: '', expiry_month: 12, expiry_year: 2027, cvv: '' })
  const [selectedPlan, setSelectedPlan] = useState('')
  const activeState = useLoad(async () => { try { return (await api.get('/subscriptions/me')).data } catch (failure) { if (failure.response?.status === 404) return null; throw failure } }, [])
  const { data: availablePlans = [] } = useLoad(async () => (await api.get('/subscriptions/plans')).data, [])
  useEffect(() => { if (!activeState.loading) setActive(activeState.data) }, [activeState.data, activeState.loading])
  const buyPlan = async (event) => {
    event.preventDefault(); setBusy(selectedPlan); setError('')
    try {
      const payload = { plan_type: selectedPlan, card }
      if (active) await api.patch('/subscriptions/me', payload)
      else await api.post('/subscriptions', payload)
      setActive((await api.get('/subscriptions/me')).data)
      setSelectedPlan('')
    } catch (failure) { setError(getErrorMessage(failure)) } finally { setBusy('') }
  }
  const cancel = async () => { setError(''); try { await api.post('/subscriptions/cancel'); setActive(null) } catch (failure) { setError(getErrorMessage(failure)) } }
  const packageDetails = useMemo(() => (availablePlans ?? []).length ? availablePlans : plans.map((plan) => ({ plan_type: plan.key, name: plan.title, price: Number(plan.price.replace(',', '.')), credits: plan.credits === '∞' ? -1 : Number(plan.credits), guest_credits: 0, priority: false })), [availablePlans])
  return <section className="section-block page-section"><div className="section-heading"><div><span className="section-kicker">KAHVENE GÖRE SEÇ</span><h1>{text('plans')}</h1><p>{text('plansBody')}</p></div>{active && <div className="active-plan-pill"><BadgeCheck size={16} /> {active.plan_type} · {active.remaining_credits === -1 ? 'Sınırsız' : `${active.remaining_credits} hak`}</div>}</div>{error && <div className="notice notice-error">{error}</div>}{activeState.error && <div className="notice notice-error">{activeState.error}</div>}<div className="plan-grid">{packageDetails.map((plan) => { const planInfo = plans.find((item) => item.key === plan.plan_type); const isCurrent = active?.plan_type === plan.plan_type; return <article className={`plan-card ${planInfo?.featured ? 'plan-featured' : ''} ${isCurrent ? 'plan-current' : ''}`} key={plan.plan_type}>{planInfo?.featured && <span className="popular-label">EN ÇOK TERCİH EDİLEN</span>}<span className="plan-symbol"><Coffee size={19} /></span><h2>{plan.name}</h2><p>{planInfo?.label || 'Kahve molanı dilediğin gibi yaşa.'}</p><div className="plan-price"><strong>{plan.price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</strong><span>₺ {text('perMonth')}</span></div><div className="plan-credit"><BadgeCheck size={16} /> {plan.credits === -1 ? text('unlimited') : `${plan.credits} ${text('coffees')}`}</div>{plan.guest_credits > 0 && <div className="plan-extra">+ {plan.guest_credits} misafir hakkı</div>}{plan.priority && <div className="plan-extra">Öncelikli hazırlama</div>}{isCurrent ? <button className="button button-current button-wide" disabled>Mevcut planın</button> : <button className={`button ${planInfo?.featured ? 'button-yellow' : 'button-outline'} button-wide`} onClick={() => setSelectedPlan(plan.plan_type)}>{active ? (planInfo && plans.findIndex((p) => p.key === plan.key) < plans.findIndex((p) => p.key === active.plan_type) ? 'Paketi düşür' : 'Paketi yükselt') : text('choose')} <ArrowRight size={15} /></button>}</article> })}</div>{selectedPlan && <form className="card-form" onSubmit={buyPlan}><div className="card-form-head"><div><span className="section-kicker">GÜVENLİ ÖDEME SİMÜLASYONU</span><h2>{plans.find((item) => item.key === selectedPlan)?.title} planı</h2></div><button type="button" className="icon-button" onClick={() => setSelectedPlan('')} aria-label="Kapat"><X size={18} /></button></div><div className="card-form-grid"><label>Kart üzerindeki ad<input required value={card.card_holder} onChange={(event) => setCard({ ...card, card_holder: event.target.value })} placeholder="Ad Soyad" /></label><label>Kart numarası<input required inputMode="numeric" maxLength={16} value={card.card_number} onChange={(event) => setCard({ ...card, card_number: event.target.value.replace(/\D/g, '') })} placeholder="4242 4242 4242 4242" /></label><label>Son kullanma ayı<input required type="number" min="1" max="12" value={card.expiry_month} onChange={(event) => setCard({ ...card, expiry_month: Number(event.target.value) })} /></label><label>Yıl<input required type="number" min="2026" max="2099" value={card.expiry_year} onChange={(event) => setCard({ ...card, expiry_year: Number(event.target.value) })} /></label><label>CVV<input required maxLength={3} inputMode="numeric" value={card.cvv} onChange={(event) => setCard({ ...card, cvv: event.target.value.replace(/\D/g, '') })} placeholder="123" /></label></div><div className="payment-hint"><CreditCard size={16} /> Demo: 4242 ile biten kart başarılı, 4000 ile biten kart başarısız olur. Gerçek ödeme yapılmaz.</div><button className="button button-yellow" disabled={Boolean(busy)}>{busy ? text('loading') : 'Ödemeyi tamamla'} <ArrowRight size={16} /></button></form>}{active && <div className="cancel-row"><div><strong>Aboneliği iptal et</strong><span>Mevcut kahve hakkın dönem sonuna kadar korunur.</span></div><button className="button button-outline" onClick={cancel}>İptal et</button></div>}</section>
}

function NotFound({ text }) { return <div className="empty-state panel-empty"><Coffee size={26} /><strong>Bu sayfayı bulamadık.</strong><Link to="/home">{text('navHome')} <ArrowRight size={14} /></Link></div> }

function AppContent() {
  const { text, toggleLanguage } = useCopy()
  return <AppFrame text={text} toggleLanguage={toggleLanguage}><Routes>
    <Route path="/" element={<AuthPage text={text} />} />
    <Route path="/home" element={<HomePage text={text} />} />
    <Route path="/login" element={<AuthPage text={text} />} />
    <Route path="/register" element={<AuthPage text={text} />} />
    <Route path="/shops/:shopId" element={<ShopPage text={text} />} />
    <Route path="/shops/:shopId/order" element={<OrderPage text={text} />} />
    <Route path="/qr/:orderId" element={<QrPage text={text} />} />
    <Route path="/history" element={<HistoryPage text={text} />} />
    <Route path="/subscription" element={<SubscriptionPage text={text} />} />
    <Route path="*" element={<NotFound text={text} />} />
  </Routes></AppFrame>
}

export default function App() { return <BrowserRouter><AppContent /></BrowserRouter> }
