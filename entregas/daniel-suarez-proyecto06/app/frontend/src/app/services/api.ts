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

  /** RF5 — Espacios libres compatibles con un tipo de vehículo. */
  getEspaciosLibres(idTipo: number): Observable<Lista<EspacioLibre>> {
    // El backend espera ?id_tipo=N como parámetro de consulta (query param).
    return this.http.get<Lista<EspacioLibre>>(
      `${this.baseUrl}/espacios/libres`,
      { params: { id_tipo: idTipo } }
    );
  }
}
