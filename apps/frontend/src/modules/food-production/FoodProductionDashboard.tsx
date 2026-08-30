import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid2'
import { Download, GlassWater, ListChecks, RefreshCw, Sparkles, TriangleAlert } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { EmptyState, ErrorState, LoadingState, PageHeader, SectionCard, StatCard } from '../../shared/components'
import { ApiError, apiDownload, apiRequest, MealTime, ProductionConsolidated } from '../../shared/services/api'


const LABELS: Record<MealTime, string> = {
  breakfast: 'Desayuno', morning_snack: 'Colación AM', lunch: 'Almuerzo',
  afternoon_snack: 'Once', dinner: 'Cena', night_snack: 'Colación PM',
}
const MEALS = Object.keys(LABELS) as MealTime[]
function today() { return new Date().toISOString().slice(0, 10) }
function message(error: unknown) { return error instanceof ApiError ? error.message : 'No fue posible cargar el consolidado.' }

export function FoodProductionDashboard() {
  const [serviceDate, setServiceDate] = useState(today())
  const [mealTime, setMealTime] = useState<MealTime | ''>('')
  const [data, setData] = useState<ProductionConsolidated | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const query = new URLSearchParams({ service_date: serviceDate })
      if (mealTime) query.set('meal_time', mealTime)
      setData(await apiRequest(`/food-production/consolidated?${query}`))
    } catch (caught) { setError(message(caught)) } finally { setLoading(false) }
  }, [mealTime, serviceDate])

  useEffect(() => { void load() }, [load])

  async function download() {
    setDownloading(true); setError(null)
    try {
      const query = new URLSearchParams({ service_date: serviceDate })
      if (mealTime) query.set('meal_time', mealTime)
      const blob = await apiDownload(`/food-production/consolidated.xlsx?${query}`)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `consolidado-raciones-${serviceDate}${mealTime ? `-${mealTime}` : ''}.xlsx`
      document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url)
    } catch (caught) { setError(message(caught)) } finally { setDownloading(false) }
  }

  const summaries = data?.summaries ?? []
  const preparations = data?.preparations ?? []
  const rations = data?.rations ?? []
  const modularPreparations = data?.modular_preparations ?? []
  const exceptions = data?.exceptions ?? []
  const totalRations = summaries.reduce((total, row) => total + row.total_rations, 0)
  const specialRations = summaries.reduce((total, row) => total + row.special_rations, 0)

  return <Stack spacing={2.5}>
    <PageHeader eyebrow="Operación de Alimentación" title="Producción alimentaria" description="Consolidado dinámico de bandejas, raciones especiales y preparaciones enterales." actions={<Stack direction="row" gap={1}><Button startIcon={<RefreshCw size={17} />} onClick={() => void load()}>Actualizar</Button><Button variant="contained" startIcon={<Download size={17} />} disabled={downloading} onClick={() => void download()}>Descargar Excel</Button></Stack>} />
    <Card variant="outlined"><CardContent><Grid container spacing={2} alignItems="center"><Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="date" label="Fecha de producción" value={serviceDate} onChange={(event) => setServiceDate(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} /></Grid><Grid size={{ xs: 12, md: 4 }}><FormControl fullWidth><InputLabel>Tiempo de comida</InputLabel><Select label="Tiempo de comida" value={mealTime} onChange={(event) => setMealTime(event.target.value as MealTime | '')}><MenuItem value="">Día completo</MenuItem>{MEALS.map((meal) => <MenuItem key={meal} value={meal}>{LABELS[meal]}</MenuItem>)}</Select></FormControl></Grid><Grid size={{ xs: 12, md: 4 }}><Typography variant="body2" color="text.secondary">Sin horario de cierre. Cada descarga registra su momento de generación.</Typography></Grid></Grid></CardContent></Card>
    {error && <ErrorState message={error} onRetry={() => void load()} />}
    {loading && !data ? <LoadingState label="Consolidando producción" rows={5} /> : data && <>
      <Grid container spacing={2}><Grid size={{ xs: 12, md: 3 }}><StatCard label="Raciones" value={totalRations} icon={<ListChecks size={20} />} /></Grid><Grid size={{ xs: 12, md: 3 }}><StatCard label="Especiales" value={specialRations} icon={<Sparkles size={20} />} tone="warning" /></Grid><Grid size={{ xs: 12, md: 3 }}><StatCard label="Preparaciones NE" value={modularPreparations.length} icon={<GlassWater size={20} />} tone="secondary" /></Grid><Grid size={{ xs: 12, md: 3 }}><StatCard label="Excepciones" value={exceptions.length} icon={<TriangleAlert size={20} />} tone="warning" /></Grid></Grid>
      {exceptions.length > 0 && <Alert severity="warning">Hay {exceptions.length} hospitalizaciones que requieren revisión antes de preparar.</Alert>}
      <SectionCard title="Resumen por servicio y tiempo"><TableContainer><Table size="small"><TableHead><TableRow><TableCell>Servicio</TableCell><TableCell>Tiempo</TableCell><TableCell align="right">Estándar</TableCell><TableCell align="right">Especiales</TableCell><TableCell align="right">Total</TableCell></TableRow></TableHead><TableBody>{summaries.map((row) => <TableRow key={`${row.service_id}-${row.meal_time}`}><TableCell>{row.service_name}</TableCell><TableCell>{LABELS[row.meal_time]}</TableCell><TableCell align="right">{row.standard_rations}</TableCell><TableCell align="right">{row.special_rations}</TableCell><TableCell align="right"><strong>{row.total_rations}</strong></TableCell></TableRow>)}</TableBody></Table></TableContainer>{!summaries.length && <EmptyState title="Sin raciones" description="No hay bandejas finalizadas para los filtros seleccionados." />}</SectionCard>
      <SectionCard title="Detalle de preparación"><TableContainer><Table size="small"><TableHead><TableRow><TableCell>Servicio</TableCell><TableCell>Tiempo</TableCell><TableCell>Preparación</TableCell><TableCell align="right">Cantidad</TableCell><TableCell>Unidad</TableCell><TableCell align="right">Pacientes</TableCell></TableRow></TableHead><TableBody>{preparations.map((row) => <TableRow key={`${row.service_name}-${row.meal_time}-${row.item_name}-${row.unit}`}><TableCell>{row.service_name}</TableCell><TableCell>{LABELS[row.meal_time]}</TableCell><TableCell>{row.item_name}</TableCell><TableCell align="right">{row.quantity}</TableCell><TableCell>{row.unit}</TableCell><TableCell align="right">{row.patient_count}</TableCell></TableRow>)}</TableBody></Table></TableContainer></SectionCard>
      <SectionCard title="Raciones especiales"><Stack spacing={1.5}>{rations.filter((row) => row.is_special).map((row) => <Card variant="outlined" key={`${row.admission_id}-${row.meal_time}`}><CardContent><Stack spacing={1}><Stack direction="row" gap={1} flexWrap="wrap"><Typography fontWeight={800}>{row.patient_name}</Typography><Chip size="small" label={`${row.service_name} · ${row.room_name} · ${row.bed_name}`} /><Chip size="small" label={LABELS[row.meal_time]} /><Chip size="small" color="warning" label={`${row.ration_count} ${row.ration_count === 1 ? 'ración' : 'raciones'}`} /></Stack><Typography>{row.items.join(' · ')}</Typography>{row.instructions && <Alert severity="warning">{row.instructions}</Alert>}{row.food_safety_alerts.length > 0 && <Alert severity="error">Alerta alimentaria: {row.food_safety_alerts.join(', ')}</Alert>}</Stack></CardContent></Card>)}{!rations.some((row) => row.is_special) && <EmptyState title="Sin especiales" description="No hay raciones especiales para los filtros seleccionados." />}</Stack></SectionCard>
      <SectionCard title="Preparaciones enterales y modulares"><TableContainer><Table size="small"><TableHead><TableRow><TableCell>Paciente / ubicación</TableCell><TableCell>Entrega</TableCell><TableCell>Preparación</TableCell><TableCell>Disolución</TableCell><TableCell>Indicaciones</TableCell></TableRow></TableHead><TableBody>{modularPreparations.map((row) => <TableRow key={`${row.admission_id}-${row.delivery}-${row.product_name}`}><TableCell><strong>{row.patient_name}</strong><br />{row.service_name} · {row.room_name} · {row.bed_name}</TableCell><TableCell>{LABELS[row.delivery as MealTime] ?? row.delivery}</TableCell><TableCell>{row.units_per_delivery} vaso(s) · {row.product_name} {row.powder_grams} g</TableCell><TableCell>{row.dilution_volume_ml} mL de {row.diluent}</TableCell><TableCell>{row.instructions}</TableCell></TableRow>)}</TableBody></Table></TableContainer>{!modularPreparations.length && <EmptyState title="Sin preparaciones NE" description="No hay bolos o preparaciones modulares para los filtros seleccionados." />}</SectionCard>
      <SectionCard title="Excepciones de control"><TableContainer><Table size="small"><TableHead><TableRow><TableCell>Paciente</TableCell><TableCell>Ubicación</TableCell><TableCell>Motivo</TableCell></TableRow></TableHead><TableBody>{exceptions.map((row) => <TableRow key={row.admission_id}><TableCell>{row.patient_name}</TableCell><TableCell>{[row.service_name, row.room_name, row.bed_name].filter(Boolean).join(' · ') || 'Sin ubicación'}</TableCell><TableCell>{row.reason}</TableCell></TableRow>)}</TableBody></Table></TableContainer></SectionCard>
    </>}
  </Stack>
}
