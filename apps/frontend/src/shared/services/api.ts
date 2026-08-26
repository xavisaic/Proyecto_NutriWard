export interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
  roles: string[]
  created_at: string
  updated_at: string
}

export interface Session {
  user: User
  csrf_token: string
}

export interface UserList {
  items: User[]
  total: number
}

export interface Role {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
}

export interface RoleList {
  items: Role[]
  total: number
}

export interface NutritionistServiceAssignment {
  id: string
  nutritionist_user_id: string
  nutritionist_name: string
  nutritionist_email: string
  service_id: string
  service_code: string
  service_name: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface NutritionistServiceAssignmentList {
  items: NutritionistServiceAssignment[]
  total: number
}

export type CareUnitType = 'bed' | 'stretcher' | 'station' | 'box'

export interface CareUnitLayout {
  id: string
  care_unit_id: string
  grid_x: number
  grid_y: number
  width: number
  height: number
  created_at: string
  updated_at: string
}

export interface HospitalCareUnit {
  id: string
  room_id: string
  code: string
  label: string | null
  unit_type: CareUnitType
  is_active: boolean
  layout: CareUnitLayout | null
  created_at: string
  updated_at: string
}

export interface HospitalRoom {
  id: string
  service_id: string
  code: string
  name: string
  floor: string | null
  notes: string | null
  is_active: boolean
  care_units: HospitalCareUnit[]
  created_at: string
  updated_at: string
}

export interface HospitalService {
  id: string
  code: string
  name: string
  description: string | null
  is_active: boolean
  rooms: HospitalRoom[]
  created_at: string
  updated_at: string
}

export interface HospitalStructure {
  items: HospitalService[]
  total: number
}

export interface BedMapLayout {
  grid_x: number
  grid_y: number
  width: number
  height: number
}

export interface BedMapPatient {
  id: string
  display_name: string
  identity_status: IdentityStatus
  age_years: number | null
  age_is_estimated: boolean
}

export interface BedMapAdmission {
  id: string
  admission_identifier: string
  status: 'active'
  admitted_at: string
}

export interface BedMapBed {
  id: string
  code: string
  label: string | null
  status: 'free' | 'occupied'
  layout: BedMapLayout | null
  occupancy: {
    patient: BedMapPatient
    admission: BedMapAdmission
    pending_transfer: {
      id: string
      status: 'pending_reception' | 'pending_bed'
      destination_service_id: string
      destination_service_code: string
      destination_service_name: string
      requested_at: string
    } | null
  } | null
}

export interface BedMapRoom {
  id: string
  code: string
  name: string
  floor: string | null
  beds: BedMapBed[]
}

export interface BedMap {
  generated_at: string
  service: Pick<HospitalService, 'id' | 'code' | 'name'>
  rooms: BedMapRoom[]
}

export type IdentityStatus = 'unidentified' | 'provisional' | 'identified'
export type AdmissionStatus = 'active' | 'discharged' | 'deceased' | 'closed'

export interface PatientLocation {
  id: string
  admission_id: string
  care_unit_id: string
  started_at: string
  ended_at: string | null
  reason: string | null
  assigned_by_user_id: string | null
  ended_by_user_id: string | null
  created_at: string
  care_unit_code: string | null
  care_unit_label: string | null
  room_id: string | null
  room_code: string | null
  room_name: string | null
  service_id: string | null
  service_code: string | null
  service_name: string | null
}

export interface Admission {
  id: string
  patient_id: string
  admission_identifier: string
  status: AdmissionStatus
  admitted_at: string
  ended_at: string | null
  end_reason: string | null
  created_at: string
  updated_at: string
  current_location: PatientLocation | null
  status_history: Array<{
    id: string
    from_status: AdmissionStatus | null
    to_status: AdmissionStatus
    reason: string | null
    changed_at: string
  }>
  location_history: PatientLocation[]
}

export interface Patient {
  id: string
  identity_status: IdentityStatus
  temporary_identifier: string | null
  rut: string | null
  given_names: string | null
  first_surname: string | null
  second_surname: string | null
  date_of_birth: string | null
  date_of_birth_is_estimated: boolean
  sex: 'female' | 'male' | 'intersex' | 'unknown' | null
  hospital_identifier: string | null
  phone: string | null
  provisional_description: string | null
  identified_at: string | null
  merged_into_patient_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  active_admission: Admission | null
  admissions?: Admission[]
}

export interface PatientList {
  items: Patient[]
  total: number
  page: number
  page_size: number
}

export interface PotentialPatientMatches {
  items: Patient[]
  total: number
}

export interface AdmissionList {
  items: Admission[]
  total: number
}

export interface PatientChartAge {
  value: number | null
  unit: 'days' | 'months' | 'years' | null
  is_estimated: boolean
  reference_date: string
  display: string
}

export interface PatientChartLocation {
  id: string
  care_unit_id: string
  care_unit_code: string
  care_unit_label: string | null
  room_id: string
  room_code: string
  room_name: string
  service_id: string
  service_code: string
  service_name: string
  started_at: string
  ended_at: string | null
  reason: string | null
  is_current: boolean
}

export interface PatientChartTransfer {
  id: string
  status: TransferStatus
  transfer_mode: TransferMode
  requested_at: string
  request_reason: string | null
  origin_service_id: string
  origin_service_code: string
  origin_service_name: string
  destination_service_id: string
  destination_service_code: string
  destination_service_name: string
}

export interface PatientChartAdmission {
  id: string
  admission_identifier: string
  status: AdmissionStatus
  admitted_at: string
  ended_at: string | null
  end_reason: string | null
  duration_days: number
  is_historical: boolean
  location: PatientChartLocation | null
  bed_status: 'occupied' | 'unassigned' | 'released'
  open_transfer: PatientChartTransfer | null
  age_at_admission: PatientChartAge
}

export interface OperationalTimelineLocation {
  care_unit_id: string | null
  care_unit_code: string | null
  care_unit_label: string | null
  room_id: string | null
  room_code: string | null
  room_name: string | null
  service_id: string
  service_code: string
  service_name: string
}

export interface OperationalTimelineEvent {
  id: string
  event_type: string
  occurred_at: string
  title: string
  description: string
  reason: string | null
  status: string | null
  origin: OperationalTimelineLocation | null
  destination: OperationalTimelineLocation | null
}

export interface OperationalTimeline {
  admission_id: string
  items: OperationalTimelineEvent[]
  total: number
  page: number
  page_size: number
}

export interface PatientChartSummary {
  patient: {
    id: string
    identity_status: IdentityStatus
    display_name: string
    temporary_identifier: string | null
    rut: string | null
    hospital_identifier: string | null
    date_of_birth: string | null
    date_of_birth_is_estimated: boolean
    sex: Patient['sex']
    phone: string | null
    provisional_description: string | null
    merged_into_patient_id: string | null
    is_active: boolean
    current_age: PatientChartAge
  }
  selected_admission: PatientChartAdmission | null
  admissions: PatientChartAdmission[]
  total_admissions: number
  recent_operational_events: OperationalTimelineEvent[]
}

export type NutritionEncounterStatus = 'draft' | 'finalized' | 'corrected' | 'cancelled'
export type NutritionPopulation = 'adult' | 'pediatric' | 'neonatal' | 'pregnancy'

export interface NutritionEncounterSummary {
  id: string
  admission_id: string
  encounter_datetime: string
  encounter_type: string
  author_professional_id: string
  author_name: string
  status: NutritionEncounterStatus
  clinical_summary: string | null
  finalized_at: string | null
  corrected_encounter_id: string | null
  version: number
  documented_sections: string[]
}

export interface NutritionEncounterList {
  items: NutritionEncounterSummary[]
  total: number
  page: number
  page_size: number
}

export interface NutritionAdvancedMeasurementValue {
  id: string
  measurement_code: string
  body_site: string | null
  laterality: 'none' | 'left' | 'right' | 'bilateral'
  attempt_number: number | null
  value: number | string
  unit: string
  value_nature: 'measured' | 'calculated' | 'device_reported'
  observations: string | null
}

export interface NutritionAdvancedMeasurementSession {
  id: string
  session_type: 'circumference' | 'handgrip' | 'skinfold_4' | 'bioimpedance'
  measured_at: string
  protocol_code: string
  protocol_version: string
  algorithm_version: string | null
  device_manufacturer: string | null
  device_model: string | null
  device_serial: string | null
  technology: string | null
  frequencies_khz: string | null
  position: string | null
  source: string | null
  reliability: 'high' | 'medium' | 'low' | 'unknown'
  preparation_status: 'standard' | 'nonstandard' | 'unknown' | null
  fasting_hours: number | string | null
  recent_exercise: boolean | null
  bladder_emptied: boolean | null
  hydration_status: 'usual' | 'altered' | 'unknown' | null
  edema_present: boolean | null
  observations: string | null
  values: NutritionAdvancedMeasurementValue[]
}

export interface NutritionEncounterRead {
  encounter: NutritionEncounterSummary & {
    reason_for_assessment: string | null
    information_source: string | null
    correction_reason: string | null
    cancellation_reason: string | null
  }
  author_name: string
  finalized_by_name: string | null
  assessment: Record<string, unknown> | null
  context_items: Array<Record<string, unknown>>
  anthropometry: Array<Record<string, unknown>>
  advanced_measurements?: NutritionAdvancedMeasurementSession[]
  screenings: Array<Record<string, unknown>>
  requirements: Array<Record<string, unknown>>
  diagnoses: Array<Record<string, unknown>>
  prescription: (Record<string, unknown> & { meal_times?: Array<Record<string, unknown>> }) | null
  monitoring: Array<Record<string, unknown>>
  intake: Array<Record<string, unknown>>
  labs: Array<Record<string, unknown>>
  alerts: Array<Record<string, unknown>>
}

export interface NutritionProjectionList {
  items: Array<Record<string, unknown>>
  total: number
  page: number
  page_size: number
}

export interface NutritionLatest {
  admission_id: string
  latest_encounter: (Record<string, unknown> & { professional_name?: string }) | null
  latest_screening: Record<string, unknown> | null
  nutritional_status: string | null
  active_diagnoses: Array<Record<string, unknown>>
  current_prescription: Record<string, unknown> | null
  adopted_requirements: Array<Record<string, unknown>>
  active_alerts: Array<Record<string, unknown>>
  suggested_reassessment_at: string | null
}

export interface ClinicalStatusHistory {
  id: string
  sequence_number: number
  from_clinical_status: string | null
  to_clinical_status: string
  from_verification_status: string | null
  to_verification_status: string
  reason: string
  source: string
  changed_by_user_id: string
  changed_at: string
  version: number
}

export interface PatientCondition {
  id: string
  patient_id: string
  condition_name: string
  code_system: string | null
  code: string | null
  clinical_status: string
  verification_status: string
  onset_date: string | null
  resolved_on: string | null
  source: string
  note: string | null
  version: number
  history: ClinicalStatusHistory[]
}

export interface AdmissionDiagnosis {
  id: string
  admission_id: string
  diagnosis_name: string
  code_system: string | null
  code: string | null
  diagnosis_type: string
  clinical_status: string
  verification_status: string
  present_on_admission: boolean
  diagnosed_at: string
  resolved_at: string | null
  source: string
  note: string | null
  version: number
  history: ClinicalStatusHistory[]
}

export interface AdmissionClinicalHistoryVersion {
  id: string
  admission_id: string
  version: number
  narrative: string
  event_start_date: string | null
  source: string
  change_reason: string | null
  recorded_by_user_id: string
  author_name: string
  recorded_at: string
}

export interface AdmissionClinicalHistory {
  admission_id: string
  current: AdmissionClinicalHistoryVersion
  versions: AdmissionClinicalHistoryVersion[]
}

export interface ClinicalContext {
  admission_id: string
  patient_id: string
  episode_history: AdmissionClinicalHistory | null
  diagnoses: AdmissionDiagnosis[]
  conditions: PatientCondition[]
}

export interface AllergyReaction {
  id: string
  manifestation: string
  severity: string | null
  occurred_at: string | null
  exposure_route: string | null
  note: string | null
  created_at: string
}

export interface AllergyStatusHistory {
  id: string
  sequence_number: number
  from_clinical_status: string | null
  to_clinical_status: string | null
  from_verification_status: string | null
  to_verification_status: string
  from_criticality: string | null
  to_criticality: string
  reason: string
  source: string
  changed_at: string
  version: number
}

export interface AllergyIntolerance {
  id: string
  patient_id: string
  asserted_admission_id: string | null
  substance_name: string
  code_system: string | null
  code: string | null
  allergy_type: string | null
  category: string
  clinical_status: string | null
  verification_status: string
  criticality: string
  onset_date: string | null
  source: string
  note: string | null
  version: number
  reactions: AllergyReaction[]
  history: AllergyStatusHistory[]
}

export interface AllergyReviewAssertion {
  id: string
  patient_id: string
  admission_id: string
  category: string
  assertion: string
  source: string
  note: string | null
  recorded_at: string
}

export interface AllergyContext {
  admission_id: string
  patient_id: string
  items: AllergyIntolerance[]
  review_assertions: AllergyReviewAssertion[]
}

export interface FoodSafetyAllergyProjection {
  admission_id: string
  review_status: 'active_food_risks' | 'no_known' | 'not_reviewed' | 'information_unavailable' | 'no_active_food_risks'
  items: Array<{
    id: string
    substance_name: string
    allergy_type: string | null
    criticality: string
    reactions: Array<{ manifestation: string; severity: string | null }>
  }>
}

export interface MedicationCatalogItem {
  code: string
  alternate_code: string | null
  display_name: string
  route: string | null
  available_inpatient: boolean
  available_outpatient: boolean
  restriction: string | null
  clinical_profile: 'standard' | 'intravenous' | 'continuous_infusion'
  default_category: string
  source_version: string
}

export interface MedicationCatalogList {
  items: MedicationCatalogItem[]
  total: number
}

export interface MedicationCatalogMatchItem {
  source_text: string
  status: 'matched' | 'ambiguous' | 'unmatched'
  match: MedicationCatalogItem | null
  suggestions: MedicationCatalogItem[]
}

export interface MedicationCatalogMatchResponse {
  items: MedicationCatalogMatchItem[]
}

export interface TreatmentVersion {
  id: string
  treatment_id: string
  version: number
  previous_version_id: string | null
  medication_catalog_code: string | null
  raw_medication_text: string | null
  name: string
  category: string
  prescription_text: string
  concentration_value: number | string | null
  concentration_unit: string | null
  diluent_volume_ml: number | string | null
  dose_value: number | string | null
  dose_unit: string | null
  route: string | null
  modality: string | null
  frequency: string | null
  rate_value: number | string | null
  rate_unit: string | null
  infusion_duration_hours: number | string | null
  administered_volume_ml: number | string | null
  estimated_volume_ml: number | string | null
  medication_catalog: MedicationCatalogItem | null
  prescribed_energy_kcal_day: number | string | null
  starts_at: string | null
  planned_ends_at: string | null
  indication: string | null
  order_status: string
  source_type: string
  source_reference: string | null
  observed_at: string
  verification_status: string
  verified_at: string | null
  verified_by_user_id: string | null
  verifier_name: string | null
  nutritional_note: string | null
  change_reason: string
  created_by_user_id: string
  author_name: string
  created_at: string
}

export interface AdmissionTreatment {
  id: string
  admission_id: string
  kind: 'medication' | 'nutritional_support'
  created_by_user_id: string
  created_at: string
  current: TreatmentVersion
  history: TreatmentVersion[]
}

export interface TreatmentReview {
  id: string
  admission_id: string
  assertion: 'reviewed_with_findings' | 'no_known' | 'information_unavailable'
  source_type: string
  note: string | null
  recorded_by_user_id: string
  author_name: string
  recorded_at: string
}

export interface TreatmentContext {
  admission_id: string
  review_status: 'not_reviewed' | 'reviewed_with_findings' | 'no_known' | 'information_unavailable'
  latest_review: TreatmentReview | null
  items: AdmissionTreatment[]
  counts: {
    active: number
    on_hold: number
    pending_verification: number
    historical: number
  }
}

export interface TreatmentImpactSummary {
  admission_id: string
  potential_energy_kcal_day: number | string
  energy_source_count: number
  items: Array<{
    treatment_id: string
    treatment_name: string
    rule_code: string
    kind: 'potential_energy' | 'missing_data' | 'consideration'
    message: string
    severity: 'info' | 'warning'
  }>
  disclaimer: string
}

export type TransferMode = 'direct' | 'reception_tray'
export type TransferStatus =
  | 'requested'
  | 'pending_reception'
  | 'accepted'
  | 'pending_bed'
  | 'assigned_to_bed'
  | 'rejected'
  | 'returned'
  | 'cancelled'

export interface TransferRequest {
  id: string
  admission_id: string
  transfer_mode: TransferMode
  status: TransferStatus
  request_reason: string | null
  requested_by_user_id: string
  requested_at: string
  completed_at: string | null
  created_at: string
  updated_at: string
  origin_service: Pick<HospitalService, 'id' | 'code' | 'name'>
  destination_service: Pick<HospitalService, 'id' | 'code' | 'name'>
  origin_care_unit_id: string
  destination_care_unit_id: string | null
  current_origin_location: {
    care_unit_id: string
    care_unit_code: string
    care_unit_label: string | null
    room_id: string
    room_code: string
    room_name: string
    service_id: string
    service_code: string
    service_name: string
  } | null
  patient: BedMapPatient
  admission: BedMapAdmission
  has_coverage_support: boolean
  status_history: Array<{
    id: string
    sequence_number: number
    from_status: TransferStatus | null
    to_status: TransferStatus
    reason: string | null
    changed_by_user_id: string
    changed_at: string
    is_coverage: boolean
  }>
}

export interface TransferRequestList {
  items: TransferRequest[]
  total: number
  page: number
  page_size: number
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  csrfToken?: string,
): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) {
    headers.set('Content-Type', 'application/json')
  }
  if (csrfToken) {
    headers.set('X-CSRF-Token', csrfToken)
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(response.status, payload?.detail ?? 'No fue posible completar la solicitud.')
  }

  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}
