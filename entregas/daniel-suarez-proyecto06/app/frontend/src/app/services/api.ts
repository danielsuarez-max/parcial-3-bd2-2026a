import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// ---- Tipos (interfaces) ----
// Describen la "forma" del JSON que devuelve el backend. No generan código:
// solo le dicen a TypeScript qué campos existen, para autocompletar y avisar de errores.

/** Una fila de GET /ingresos/dentro (un vehículo actualmente dentro). */
export interface VehiculoDentro {
  id_ingreso: number;
  placa: string;
  tipo_vehiculo: string;
  numero_espacio: number;
  fecha_hora_entrada: string;
  modalidad: 'MENSUAL' | 'OCASIONAL';
  cliente_mensual: string | null;
  minutos_dentro: number;
}

/** El backend envuelve las listas en { total, datos }. */
export interface Lista<T> {
  total: number;
  datos: T[];
}

/** Una fila del historial de ingresos (GET /ingresos). */
export interface IngresoHistorial {
  id_ingreso: number;
  placa: string;
  tipo_vehiculo: string;
  numero_espacio: number;
  fecha_hora_entrada: string;
  fecha_hora_salida: string | null;
  estado: 'DENTRO' | 'SALIÓ';
  modalidad: 'MENSUAL' | 'OCASIONAL';
  cliente_mensual: string | null;
  monto_cobrado: number | null;
  minutos: number;
}

/** Respuesta de GET /ocupacion (una sola fila, no lista). */
export interface Ocupacion {
  total_espacios: number;
  libres: number;
  ocupados: number;
  reservados: number;
  porcentaje_ocupacion: number;
}

/** Un tipo de vehículo (GET /tipos). */
export interface TipoVehiculoItem {
  id_tipo: number;
  nombre: string;
  descripcion: string;
}

/** Una tarifa vigente (GET /tarifas). */
export interface Tarifa {
  id_tarifa: number;
  id_tipo: number;
  tipo: string;
  valor_hora: number;
  vigente_desde: string;
}

/** Una fila del histórico de tarifas (GET /tarifas/historico). */
export interface TarifaHistorico {
  id_tarifa: number;
  tipo: string;
  valor_hora: number;
  vigente_desde: string;
  activa: number;   // 1 = vigente, 0 = jubilada
}

/** Datos para crear una tarifa nueva (POST /tarifas). */
export interface TarifaIn {
  id_tipo: number;
  valor_hora: number;
  vigente_desde?: string | null;
}

/** Un espacio libre (GET /espacios/libres). */
export interface EspacioLibre {
  id_espacio: number;
  numero: number;
}

/** Un espacio con su estado, para el mapa del parqueadero (GET /espacios). */
export interface EspacioEstado {
  id_espacio: number;
  numero: number;
  estado: 'LIBRE' | 'OCUPADO' | 'RESERVADO';
  placa: string | null;            // vehículo dentro (si está ocupado)
  reservado_para: string | null;   // cliente dueño del cupo (si está reservado)
}

/** Datos que enviamos para registrar una entrada (POST /ingresos). */
export interface EntradaIn {
  placa: string;
  id_tipo: number;
  id_espacio: number;
  color?: string | null;
  marca?: string | null;
}

/** Respuesta del backend al registrar una entrada. */
export interface EntradaOut {
  mensaje: string;
  id_ingreso: number;
  placa: string;
  modalidad: 'MENSUAL' | 'OCASIONAL';
  id_espacio: number;
  numero_espacio: number;
}

/** Respuesta del backend al registrar una salida (RF2). */
export interface SalidaOut {
  mensaje: string;
  id_ingreso: number;
  placa: string;
  tipo_vehiculo: string;
  modalidad: 'MENSUAL' | 'OCASIONAL';
  minutos_dentro: number;
  horas_cobradas?: number;     // solo ocasional
  monto_cobrado: number | null;
  nota?: string;               // solo mensual ("incluido en la mensualidad")
}

/** Una fila de la lista de mensualidades (GET /mensualidades). */
export interface Mensualidad {
  id_mensualidad: number;
  cliente: string;
  numero_espacio: number;
  estado: 'ACTIVA' | 'VENCIDA' | 'CANCELADA';
  fecha_inicio: string;
  fecha_fin: string;
  monto_pagado: number;
  placas: string[];
}

/** Datos del cliente para crear una mensualidad. */
export interface ClienteIn {
  documento: string;
  nombre_completo: string;
  telefono?: string | null;
  email?: string | null;
}

/** Un vehículo cubierto por la mensualidad. */
export interface VehiculoMensualIn {
  placa: string;
  id_tipo: number;
}

/** Datos para crear una mensualidad (POST /mensualidades).
 *  fecha_fin y monto los calcula el backend, por eso no se envían. */
export interface MensualidadIn {
  cliente: ClienteIn;
  id_espacio: number;
  fecha_inicio: string;
  vehiculos: VehiculoMensualIn[];
}

/** Valor mensual estipulado por tipo (GET /tarifas-mensuales). */
export interface TarifaMensual {
  id_tipo: number;
  tipo: string;
  valor_mes: number;
}

/** Un vehículo cubierto por una mensualidad (GET /mensualidades/{id}/vehiculos). */
export interface VehiculoDeMensualidad {
  placa: string;
  id_tipo: number;
  tipo: string;
}

/** Una mensualidad activa de una placa (GET /vehiculos/{placa}/mensualidad). */
export interface MensualidadActiva {
  id_mensualidad: number;
  id_espacio: number;
  numero_espacio: number;
  fecha_inicio: string;
  fecha_fin: string;
  nombre_completo: string;
}

@Injectable({ providedIn: 'root' })   // servicio único compartido por toda la app
export class Api {
  // Dirección base del backend (FastAPI corre en el puerto 8001).
  private readonly baseUrl = 'http://localhost:8001';

  // inject() es la forma moderna de pedirle a Angular una dependencia (aquí, HttpClient).
  private http = inject(HttpClient);

  /** RF7 — Vehículos actualmente dentro del parqueadero. */
  getVehiculosDentro(): Observable<Lista<VehiculoDentro>> {
    return this.http.get<Lista<VehiculoDentro>>(`${this.baseUrl}/ingresos/dentro`);
  }

  /** Historial de ingresos (todos). Opcional: filtrar por placa y/o modalidad. */
  getHistorial(placa?: string, modalidad?: string): Observable<Lista<IngresoHistorial>> {
    // Solo agregamos al query los filtros que tengan valor.
    const params: Record<string, string> = {};
    if (placa) params['placa'] = placa;
    if (modalidad) params['modalidad'] = modalidad;
    return this.http.get<Lista<IngresoHistorial>>(`${this.baseUrl}/ingresos`, { params });
  }

  /** Estado de ocupación (libres / ocupados / reservados / %). */
  getOcupacion(): Observable<Ocupacion> {
    return this.http.get<Ocupacion>(`${this.baseUrl}/ocupacion`);
  }

  /** Mapa del parqueadero: todos los espacios con su estado. */
  getEspacios(): Observable<Lista<EspacioEstado>> {
    return this.http.get<Lista<EspacioEstado>>(`${this.baseUrl}/espacios`);
  }

  /** Catálogo de tipos de vehículo (para llenar dropdowns). */
  getTipos(): Observable<Lista<TipoVehiculoItem>> {
    return this.http.get<Lista<TipoVehiculoItem>>(`${this.baseUrl}/tipos`);
  }

  /** RF3 — Tarifas vigentes por tipo de vehículo. */
  getTarifas(): Observable<Lista<Tarifa>> {
    return this.http.get<Lista<Tarifa>>(`${this.baseUrl}/tarifas`);
  }

  /** RF3 — Histórico de tarifas de un tipo (vigentes e inactivas). */
  getTarifaHistorico(idTipo: number): Observable<Lista<TarifaHistorico>> {
    return this.http.get<Lista<TarifaHistorico>>(
      `${this.baseUrl}/tarifas/historico`, { params: { id_tipo: idTipo } }
    );
  }

  /** RF3 — Crea una tarifa nueva (versiona: jubila la anterior). */
  postTarifa(tarifa: TarifaIn): Observable<any> {
    return this.http.post(`${this.baseUrl}/tarifas`, tarifa);
  }

  /** RF5 — Espacios libres compatibles con un tipo de vehículo. */
  getEspaciosLibres(idTipo: number): Observable<Lista<EspacioLibre>> {
    // El backend espera ?id_tipo=N como parámetro de consulta (query param).
    return this.http.get<Lista<EspacioLibre>>(
      `${this.baseUrl}/espacios/libres`,
      { params: { id_tipo: idTipo } }
    );
  }

  /** ¿La placa tiene mensualidad activa hoy? Lista vacía = es ocasional. */
  getMensualidadDePlaca(placa: string): Observable<Lista<MensualidadActiva>> {
    return this.http.get<Lista<MensualidadActiva>>(
      `${this.baseUrl}/vehiculos/${encodeURIComponent(placa)}/mensualidad`
    );
  }

  /** RF1 — Registra la entrada de un vehículo (POST: envía datos en el cuerpo). */
  postIngreso(entrada: EntradaIn): Observable<EntradaOut> {
    return this.http.post<EntradaOut>(`${this.baseUrl}/ingresos`, entrada);
  }

  /** RF2 — Registra la salida de un ingreso y calcula el cobro. */
  postSalida(idIngreso: number): Observable<SalidaOut> {
    // No hay cuerpo que enviar; el id va en la URL. Mandamos {} como cuerpo.
    return this.http.post<SalidaOut>(`${this.baseUrl}/ingresos/${idIngreso}/salida`, {});
  }

  /** RF4 — Lista de mensualidades (con cliente, cupo, placas y estado). */
  getMensualidades(): Observable<Lista<Mensualidad>> {
    return this.http.get<Lista<Mensualidad>>(`${this.baseUrl}/mensualidades`);
  }

  /** RF4 — Catálogo de valor mensual por tipo (para calcular el monto en pantalla). */
  getTarifasMensuales(): Observable<Lista<TarifaMensual>> {
    return this.http.get<Lista<TarifaMensual>>(`${this.baseUrl}/tarifas-mensuales`);
  }

  /** RF4 — Crea una mensualidad (cliente + cupo + vehículos) en una transacción. */
  postMensualidad(m: MensualidadIn): Observable<any> {
    return this.http.post(`${this.baseUrl}/mensualidades`, m);
  }

  /** RF4 — Cancela una mensualidad y libera su cupo (confirmamos directo). */
  cancelarMensualidad(id: number): Observable<any> {
    return this.http.put(`${this.baseUrl}/mensualidades/${id}/cancelar`, { confirmar: true });
  }

  /** RF4 — Vehículos cubiertos por una mensualidad (para precargar la renovación). */
  getVehiculosDeMensualidad(id: number): Observable<Lista<VehiculoDeMensualidad>> {
    return this.http.get<Lista<VehiculoDeMensualidad>>(`${this.baseUrl}/mensualidades/${id}/vehiculos`);
  }

  /** RF4 — Renueva (extiende +1 mes) una mensualidad con el set de vehículos dado. */
  renovarMensualidad(id: number, vehiculos: VehiculoMensualIn[]): Observable<any> {
    return this.http.post(`${this.baseUrl}/mensualidades/${id}/renovar`, { vehiculos });
  }

  /** RF4 — Barrido: marca VENCIDA las mensualidades activas ya expiradas. */
  vencerExpiradas(): Observable<any> {
    return this.http.post(`${this.baseUrl}/mensualidades/vencer-expiradas`, {});
  }
}
