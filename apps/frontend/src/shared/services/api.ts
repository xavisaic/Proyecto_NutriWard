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
