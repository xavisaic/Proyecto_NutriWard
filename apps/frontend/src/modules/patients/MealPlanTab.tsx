import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid2'
import { Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { EmptyState, ErrorState, LoadingState, SectionCard } from '../../shared/components'
import { ApiError, apiRequest, FoodCatalogItem, MealPlan, MealTime } from '../../shared/services/api'


const MEAL_TIMES: MealTime[] = ['breakfast', 'morning_snack', 'lunch', 'afternoon_snack', 'dinner', 'night_snack']
const MEAL_LABELS: Record<MealTime, string> = {
  breakfast: 'Desayuno', morning_snack: 'Colación AM', lunch: 'Almuerzo',
  afternoon_snack: 'Once', dinner: 'Cena', night_snack: 'Colación PM',
}

type DraftItem = {
  catalog_item_id: string | null
  custom_name: string
  display_name: string
  quantity: string
  unit: string
  instructions: string
}
type DraftSlot = {
  meal_time: MealTime
  fulfillment_status: 'ordered' | 'no_tray' | 'not_applicable' | 'hold'
  is_special: boolean
  special_instructions: string
  items: DraftItem[]
}
type DraftPreparation = {
  product_name: string
  powder_grams: string
  diluent: string
  dilution_volume_ml: string
  units_per_delivery: string
  meal_time: MealTime
  instructions: string
}
type Draft = {
  effective_from: string
  effective_until: string
  validity_mode: 'until_changed' | 'single_day' | 'date_range'
  oral_enabled: boolean
  enteral_enabled: boolean
  parenteral_enabled: boolean
  general_instructions: string
  slots: DraftSlot[]
  modular_preparations: DraftPreparation[]
}

function today() { return new Date().toISOString().slice(0, 10) }

function emptyDraft(): Draft {
  return {
    effective_from: today(), effective_until: '', validity_mode: 'until_changed',
    oral_enabled: true, enteral_enabled: false, parenteral_enabled: false,
    general_instructions: '',
    slots: MEAL_TIMES.map((meal_time) => ({
      meal_time, fulfillment_status: 'not_applicable', is_special: false,
      special_instructions: '', items: [],
    })),
    modular_preparations: [],
  }
}

function draftFromPlan(plan: MealPlan): Draft {
  const byTime = new Map(plan.slots.map((slot) => [slot.meal_time, slot]))
  return {
    effective_from: plan.effective_from,
    effective_until: plan.effective_until ?? '',
    validity_mode: plan.validity_mode,
    oral_enabled: plan.oral_enabled,
    enteral_enabled: plan.enteral_enabled,
    parenteral_enabled: plan.parenteral_enabled,
    general_instructions: plan.general_instructions ?? '',
    slots: MEAL_TIMES.map((meal_time) => {
      const slot = byTime.get(meal_time)
      return {
        meal_time,
        fulfillment_status: slot?.fulfillment_status ?? 'not_applicable',
        is_special: slot?.is_special ?? false,
        special_instructions: slot?.special_instructions ?? '',
        items: slot?.items.map((item) => ({
          catalog_item_id: item.catalog_item_id,
          custom_name: item.is_custom ? item.display_name : '',
          display_name: item.display_name,
          quantity: String(Number(item.quantity)),
          unit: item.unit,
          instructions: item.instructions ?? '',
        })) ?? [],
      }
    }),
    modular_preparations: plan.modular_preparations.map((item) => ({
      product_name: item.product_name,
      powder_grams: String(item.powder_grams),
      diluent: item.diluent,
      dilution_volume_ml: String(item.dilution_volume_ml),
      units_per_delivery: String(item.units_per_delivery),
      meal_time: item.meal_time ?? 'morning_snack',
      instructions: item.instructions ?? '',
    })),
  }
}

function payload(draft: Draft, version?: number) {
  return {
    ...(version ? { version } : {}),
    effective_from: draft.effective_from,
    effective_until: draft.validity_mode === 'date_range' ? draft.effective_until : null,
    validity_mode: draft.validity_mode,
    oral_enabled: draft.oral_enabled,
    enteral_enabled: draft.enteral_enabled,
    parenteral_enabled: draft.parenteral_enabled,
    general_instructions: draft.general_instructions || null,
    slots: draft.slots.map((slot) => ({
      meal_time: slot.meal_time,
      fulfillment_status: draft.oral_enabled ? slot.fulfillment_status : 'not_applicable',
      is_special: slot.is_special,
      special_instructions: slot.special_instructions || null,
      items: draft.oral_enabled && slot.fulfillment_status === 'ordered' ? slot.items.map((item) => ({
        catalog_item_id: item.catalog_item_id,
        custom_name: item.catalog_item_id ? null : item.custom_name,
        quantity: Number(item.quantity),
        unit: item.unit,
        instructions: item.instructions || null,
      })) : [],
    })),
    modular_preparations: draft.modular_preparations.map((item) => ({
      preparation_type: 'protein_bolus',
      product_name: item.product_name,
      powder_grams: Number(item.powder_grams),
      diluent: item.diluent,
      dilution_volume_ml: Number(item.dilution_volume_ml),
      units_per_delivery: Number(item.units_per_delivery),
      meal_time: item.meal_time,
      scheduled_time: null,
      instructions: item.instructions || null,
    })),
  }
}

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : 'No fue posible guardar la minuta.'
}

function MealPlanEditor({ open, source, catalog, csrfToken, admissionId, onClose, onSaved }: {
  open: boolean
  source: MealPlan | null
  catalog: FoodCatalogItem[]
  csrfToken: string
  admissionId: string
  onClose: () => void
  onSaved: () => void
}) {
  const editingDraft = source?.status === 'draft'
  const [draft, setDraft] = useState<Draft>(emptyDraft())
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setDraft(source ? draftFromPlan(source) : emptyDraft())
    setError(null)
  }, [open, source])

  function patchSlot(index: number, changes: Partial<DraftSlot>) {
    setDraft((current) => ({ ...current, slots: current.slots.map((slot, slotIndex) => slotIndex === index ? { ...slot, ...changes } : slot) }))
  }
  function patchItem(slotIndex: number, itemIndex: number, changes: Partial<DraftItem>) {
    const slot = draft.slots[slotIndex]
    patchSlot(slotIndex, { items: slot.items.map((item, index) => index === itemIndex ? { ...item, ...changes } : item) })
  }
  function addCatalogItem(slotIndex: number, item: FoodCatalogItem | null) {
    if (!item) return
    const slot = draft.slots[slotIndex]
    patchSlot(slotIndex, { items: [...slot.items, { catalog_item_id: item.id, custom_name: '', display_name: item.display_name, quantity: '1', unit: item.default_unit, instructions: '' }] })
  }
  function addCustomItem(slotIndex: number) {
    const slot = draft.slots[slotIndex]
    patchSlot(slotIndex, { fulfillment_status: 'ordered', is_special: true, items: [...slot.items, { catalog_item_id: null, custom_name: '', display_name: 'Preparación libre', quantity: '1', unit: 'unidad', instructions: '' }] })
  }

  async function save(finalize: boolean) {
    setSaving(true); setError(null)
    try {
      let saved: MealPlan
      if (editingDraft && source) {
        saved = await apiRequest(`/meal-plans/${source.id}`, { method: 'PUT', body: JSON.stringify(payload(draft, source.version)) }, csrfToken)
      } else {
        saved = await apiRequest(`/admissions/${admissionId}/meal-plans`, { method: 'POST', body: JSON.stringify(payload(draft)) }, csrfToken)
      }
      if (finalize) {
        await apiRequest(`/meal-plans/${saved.id}/finalize`, { method: 'POST', body: JSON.stringify({ version: saved.version }) }, csrfToken)
      }
      onSaved()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return <Dialog open={open} onClose={saving ? undefined : onClose} fullWidth maxWidth="lg">
    <DialogTitle>{editingDraft ? 'Editar minuta en borrador' : 'Nueva minuta diaria'}</DialogTitle>
    <DialogContent dividers>
      <Stack spacing={2.5}>
        {error && <Alert severity="error">{error}</Alert>}
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="date" label="Vigente desde" value={draft.effective_from} onChange={(event) => setDraft({ ...draft, effective_from: event.target.value })} slotProps={{ inputLabel: { shrink: true } }} /></Grid>
          <Grid size={{ xs: 12, md: 4 }}><FormControl fullWidth><InputLabel>Vigencia</InputLabel><Select label="Vigencia" value={draft.validity_mode} onChange={(event) => setDraft({ ...draft, validity_mode: event.target.value as Draft['validity_mode'] })}><MenuItem value="until_changed">Hasta ser reemplazada</MenuItem><MenuItem value="single_day">Sólo este día</MenuItem><MenuItem value="date_range">Rango de fechas</MenuItem></Select></FormControl></Grid>
          {draft.validity_mode === 'date_range' && <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="date" label="Vigente hasta" value={draft.effective_until} onChange={(event) => setDraft({ ...draft, effective_until: event.target.value })} slotProps={{ inputLabel: { shrink: true } }} /></Grid>}
        </Grid>
        <Box><Typography fontWeight={800}>Vías activas</Typography><Stack direction="row" flexWrap="wrap"><FormControlLabel control={<Checkbox checked={draft.oral_enabled} onChange={(event) => setDraft({ ...draft, oral_enabled: event.target.checked })} />} label="Oral" /><FormControlLabel control={<Checkbox checked={draft.enteral_enabled} onChange={(event) => setDraft({ ...draft, enteral_enabled: event.target.checked })} />} label="Enteral" /><FormControlLabel control={<Checkbox checked={draft.parenteral_enabled} onChange={(event) => setDraft({ ...draft, parenteral_enabled: event.target.checked })} />} label="Parenteral" /></Stack></Box>
        {draft.oral_enabled && <Stack spacing={2}>
          <Typography variant="h6">Bandejas por tiempo de comida</Typography>
          {draft.slots.map((slot, slotIndex) => <Card key={slot.meal_time} variant="outlined"><CardContent><Stack spacing={2}>
            <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}>
              <Typography fontWeight={850}>{MEAL_LABELS[slot.meal_time]}</Typography>
              <FormControl size="small" sx={{ minWidth: 190 }}><InputLabel>Estado</InputLabel><Select label="Estado" value={slot.fulfillment_status} onChange={(event) => patchSlot(slotIndex, { fulfillment_status: event.target.value as DraftSlot['fulfillment_status'], items: event.target.value === 'ordered' ? slot.items : [] })}><MenuItem value="ordered">Solicitar bandeja</MenuItem><MenuItem value="no_tray">Sin bandeja / ayunas</MenuItem><MenuItem value="hold">Suspendida</MenuItem><MenuItem value="not_applicable">No corresponde</MenuItem></Select></FormControl>
            </Stack>
            {slot.fulfillment_status === 'ordered' && <>
              <Autocomplete options={catalog} getOptionLabel={(option) => option.display_name} value={null} onChange={(_, item) => addCatalogItem(slotIndex, item)} renderInput={(params) => <TextField {...params} label="Agregar del catálogo" placeholder="Buscar régimen, bebida, suplemento…" />} />
              {slot.items.map((item, itemIndex) => <Grid container spacing={1.5} key={`${slot.meal_time}-${itemIndex}`} alignItems="center">
                <Grid size={{ xs: 12, md: 4 }}>{item.catalog_item_id ? <Box><Typography>{item.display_name}</Typography>{catalog.find((option) => option.id === item.catalog_item_id)?.standard_recipe_note && <Typography variant="caption" color="text.secondary">{catalog.find((option) => option.id === item.catalog_item_id)?.standard_recipe_note}</Typography>}</Box> : <TextField fullWidth label="Preparación libre" value={item.custom_name} onChange={(event) => patchItem(slotIndex, itemIndex, { custom_name: event.target.value, display_name: event.target.value || 'Preparación libre' })} />}</Grid>
                <Grid size={{ xs: 5, md: 2 }}><TextField fullWidth type="number" label="Cantidad" value={item.quantity} onChange={(event) => patchItem(slotIndex, itemIndex, { quantity: event.target.value })} inputProps={{ min: item.catalog_item_id ? 1 : 0.001, step: item.catalog_item_id ? 1 : 0.5 }} helperText={item.catalog_item_id ? 'Número entero' : undefined} /></Grid>
                <Grid size={{ xs: 7, md: 2 }}><TextField fullWidth label="Unidad" value={item.unit} onChange={(event) => patchItem(slotIndex, itemIndex, { unit: event.target.value })} /></Grid>
                <Grid size={{ xs: 10, md: 3 }}><TextField fullWidth label="Indicación del ítem" value={item.instructions} onChange={(event) => patchItem(slotIndex, itemIndex, { instructions: event.target.value })} /></Grid>
                <Grid size={{ xs: 2, md: 1 }}><Button color="error" aria-label="Eliminar ítem" onClick={() => patchSlot(slotIndex, { items: slot.items.filter((_, index) => index !== itemIndex) })}><Trash2 size={18} /></Button></Grid>
              </Grid>)}
              <Button startIcon={<Plus size={17} />} onClick={() => addCustomItem(slotIndex)}>Agregar preparación libre</Button>
              <TextField fullWidth multiline minRows={2} label="Indicaciones especiales" value={slot.special_instructions} onChange={(event) => patchSlot(slotIndex, { special_instructions: event.target.value, is_special: Boolean(event.target.value) || slot.is_special })} />
              <FormControlLabel control={<Checkbox checked={slot.is_special} onChange={(event) => patchSlot(slotIndex, { is_special: event.target.checked })} />} label="Marcar como ración especial" />
            </>}
          </Stack></CardContent></Card>)}
        </Stack>}
        <Divider />
        <Stack spacing={2}>
          <Stack direction="row" justifyContent="space-between" alignItems="center"><Box><Typography variant="h6">Preparaciones modulares / NE</Typography><Typography variant="body2" color="text.secondary">Se consolidan separadas de las bandejas orales.</Typography></Box><Button startIcon={<Plus size={17} />} onClick={() => setDraft({ ...draft, modular_preparations: [...draft.modular_preparations, { product_name: 'Módulo proteico', powder_grams: '10', diluent: 'Agua', dilution_volume_ml: '80', units_per_delivery: '1', meal_time: 'morning_snack', instructions: '' }] })}>Agregar bolo</Button></Stack>
          {draft.modular_preparations.map((item, index) => <Card variant="outlined" key={index}><CardContent><Grid container spacing={1.5} alignItems="center">
            <Grid size={{ xs: 12, md: 3 }}><TextField fullWidth label="Producto" value={item.product_name} onChange={(event) => setDraft({ ...draft, modular_preparations: draft.modular_preparations.map((row, i) => i === index ? { ...row, product_name: event.target.value } : row) })} /></Grid>
            <Grid size={{ xs: 6, md: 1.5 }}><TextField fullWidth type="number" label="Polvo (g)" value={item.powder_grams} onChange={(event) => setDraft({ ...draft, modular_preparations: draft.modular_preparations.map((row, i) => i === index ? { ...row, powder_grams: event.target.value } : row) })} /></Grid>
            <Grid size={{ xs: 6, md: 1.5 }}><TextField fullWidth type="number" label="Volumen (mL)" value={item.dilution_volume_ml} onChange={(event) => setDraft({ ...draft, modular_preparations: draft.modular_preparations.map((row, i) => i === index ? { ...row, dilution_volume_ml: event.target.value } : row) })} /></Grid>
            <Grid size={{ xs: 6, md: 1.5 }}><TextField fullWidth label="Diluyente" value={item.diluent} onChange={(event) => setDraft({ ...draft, modular_preparations: draft.modular_preparations.map((row, i) => i === index ? { ...row, diluent: event.target.value } : row) })} /></Grid>
            <Grid size={{ xs: 6, md: 1.5 }}><TextField fullWidth type="number" label="Vasos" value={item.units_per_delivery} onChange={(event) => setDraft({ ...draft, modular_preparations: draft.modular_preparations.map((row, i) => i === index ? { ...row, units_per_delivery: event.target.value } : row) })} /></Grid>
            <Grid size={{ xs: 10, md: 2 }}><FormControl fullWidth><InputLabel>Entrega</InputLabel><Select label="Entrega" value={item.meal_time} onChange={(event) => setDraft({ ...draft, modular_preparations: draft.modular_preparations.map((row, i) => i === index ? { ...row, meal_time: event.target.value as MealTime } : row) })}>{MEAL_TIMES.map((time) => <MenuItem value={time} key={time}>{MEAL_LABELS[time]}</MenuItem>)}</Select></FormControl></Grid>
            <Grid size={{ xs: 2, md: 1 }}><Button color="error" aria-label="Eliminar bolo" onClick={() => setDraft({ ...draft, modular_preparations: draft.modular_preparations.filter((_, i) => i !== index) })}><Trash2 size={18} /></Button></Grid>
            <Grid size={12}><TextField fullWidth label="Indicaciones del bolo" value={item.instructions} onChange={(event) => setDraft({ ...draft, modular_preparations: draft.modular_preparations.map((row, i) => i === index ? { ...row, instructions: event.target.value } : row) })} /></Grid>
          </Grid></CardContent></Card>)}
        </Stack>
        <TextField fullWidth multiline minRows={2} label="Indicaciones generales para Alimentación" value={draft.general_instructions} onChange={(event) => setDraft({ ...draft, general_instructions: event.target.value })} />
      </Stack>
    </DialogContent>
    <DialogActions><Button onClick={onClose} disabled={saving}>Cancelar</Button><Button onClick={() => void save(false)} disabled={saving}>Guardar borrador</Button><Button variant="contained" onClick={() => void save(true)} disabled={saving}>Guardar y finalizar</Button></DialogActions>
  </Dialog>
}

export function MealPlanTab({ admissionId, historical, csrfToken }: { admissionId: string; historical: boolean; csrfToken: string }) {
  const [plan, setPlan] = useState<MealPlan | null>(null)
  const [catalog, setCatalog] = useState<FoodCatalogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [nextPlan, nextCatalog] = await Promise.all([
        apiRequest<MealPlan | null>(`/admissions/${admissionId}/meal-plans/current`),
        apiRequest<FoodCatalogItem[]>('/food-regimen-catalog'),
      ])
      setPlan(nextPlan); setCatalog(nextCatalog)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally { setLoading(false) }
  }, [admissionId])

  useEffect(() => { void load() }, [load])
  const routeLabels = useMemo(() => plan ? [plan.oral_enabled && 'Oral', plan.enteral_enabled && 'Enteral', plan.parenteral_enabled && 'Parenteral'].filter(Boolean) : [], [plan])

  return <Stack spacing={2}>
    <Alert severity="info">Sólo las minutas finalizadas alimentan el consolidado. Las preparaciones NE se cuentan separadas de las bandejas.</Alert>
    <SectionCard title="Minuta diaria" description="Selección combinable para los seis tiempos de comida y preparaciones modulares." actions={!historical && <Button variant="contained" onClick={() => setOpen(true)}>{plan?.status === 'draft' ? 'Continuar borrador' : plan ? 'Crear nueva versión' : 'Crear minuta'}</Button>}>
      {loading ? <LoadingState label="Cargando minuta" rows={4} /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : !plan ? <EmptyState title="Sin minuta" description="Cree y finalice una minuta para incorporarla a producción." /> : <Stack spacing={2}>
        <Stack direction="row" gap={1} flexWrap="wrap"><Chip label={plan.status === 'draft' ? 'Borrador' : 'Finalizada'} color={plan.status === 'draft' ? 'warning' : 'success'} /><Chip label={`Vías: ${routeLabels.join(' + ')}`} variant="outlined" /><Chip label={`Desde ${plan.effective_from}`} variant="outlined" /></Stack>
        {[...plan.slots].sort((left, right) => MEAL_TIMES.indexOf(left.meal_time) - MEAL_TIMES.indexOf(right.meal_time)).map((slot) => <Card variant="outlined" key={slot.meal_time}><CardContent><Stack spacing={1}><Stack direction="row" justifyContent="space-between"><Typography fontWeight={800}>{MEAL_LABELS[slot.meal_time]}</Typography><Chip size="small" label={slot.fulfillment_status === 'ordered' ? `${slot.items.length} ítems` : slot.fulfillment_status} /></Stack>{slot.items.map((item) => <Typography variant="body2" key={item.id}>{Number(item.quantity).toLocaleString('es-CL', { maximumFractionDigits: 3 })} {item.unit} · {item.display_name}{item.instructions ? ` — ${item.instructions}` : ''}</Typography>)}{slot.special_instructions && <Alert severity="warning">{slot.special_instructions}</Alert>}</Stack></CardContent></Card>)}
        {plan.modular_preparations.length > 0 && <Box><Typography fontWeight={800} mb={1}>Preparaciones modulares</Typography>{plan.modular_preparations.map((item) => <Typography key={item.id}>{item.units_per_delivery} vaso(s): {item.product_name} {item.powder_grams} g en {item.dilution_volume_ml} mL de {item.diluent} · {item.meal_time ? MEAL_LABELS[item.meal_time] : item.scheduled_time}</Typography>)}</Box>}
      </Stack>}
    </SectionCard>
    <MealPlanEditor open={open} source={plan} catalog={catalog} csrfToken={csrfToken} admissionId={admissionId} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); void load() }} />
  </Stack>
}
