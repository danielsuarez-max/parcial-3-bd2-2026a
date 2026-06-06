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
}
