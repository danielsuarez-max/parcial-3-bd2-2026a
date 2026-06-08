import { Component, signal, inject, DestroyRef } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { Api, VehiculoDentro, SalidaOut } from '../../services/api';

@Component({
  selector: 'app-vehiculos-dentro',
  imports: [DatePipe, DecimalPipe],
  templateUrl: './vehiculos-dentro.html',
  styleUrl: './vehiculos-dentro.css'
})
export class VehiculosDentroComponent {
  private api = inject(Api);

  vehiculos = signal<VehiculoDentro[]>([]);
  cargando = signal(true);
  error = signal<string | null>(null);

  // Estado del registro de salida
  saliendoId = signal<number | null>(null);     // id del ingreso que se está cerrando
  ultimaSalida = signal<SalidaOut | null>(null); // resultado de la última salida
  confirmando = signal<VehiculoDentro | null>(null); // vehículo cuyo modal está abierto

  // ===== Cronómetro y costo en tiempo real =====
  // 'ahora' es un reloj que avanza cada segundo. Al ser un signal, cualquier cosa que
  // lo lea (el tiempo vivo, el costo proyectado) se vuelve a pintar sola cada segundo.
  ahora = signal<number>(Date.now());
  // Instante en que recibimos la lista. Sirve de "ancla": sumamos los segundos
  // transcurridos desde aquí a los minutos_dentro que ya calculó el backend.
  // (Evitamos recalcular desde fecha_hora_entrada, que viene sin zona horaria.)
  private cargadoEn = Date.now();
  // valor_hora por nombre de tipo (ej. { Carro: 4000, Moto: 2000 }), para el costo proyectado.
  tarifaPorTipo = signal<Record<string, number>>({});

  constructor() {
    this.cargar();

    // Tarifas vigentes: las pedimos una sola vez para proyectar el cobro en pantalla.
    this.api.getTarifas().subscribe({
      next: (resp) => {
        const mapa: Record<string, number> = {};
        for (const t of resp.datos) mapa[t.tipo] = t.valor_hora;
        this.tarifaPorTipo.set(mapa);
      },
      error: (err) => console.error(err)
    });

    // Reloj: avanza cada segundo para que el cronómetro y el costo suban en vivo.
    const idReloj = setInterval(() => this.ahora.set(Date.now()), 1000);
    // Limpiamos el timer al salir de la vista para no dejar nada corriendo.
    inject(DestroyRef).onDestroy(() => clearInterval(idReloj));
  }

  /** Pide al backend la lista de vehículos dentro. Reutilizable por el botón "Actualizar". */
  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.getVehiculosDentro().subscribe({
      next: (resp) => {
        this.vehiculos.set(resp.datos);
        this.cargadoEn = Date.now();   // re-anclamos el cronómetro a los datos frescos
        this.cargando.set(false);
      },
      error: (err) => {
        console.error(err);
        this.error.set('No se pudo conectar con el backend. ¿Está corriendo en el puerto 8001?');
        this.cargando.set(false);
      }
    });
  }

  /** Minutos dentro "en vivo": base del backend + lo transcurrido desde que cargamos. */
  private minutosVivos(v: VehiculoDentro): number {
    const transcurridos = (this.ahora() - this.cargadoEn) / 60000;
    return v.minutos_dentro + transcurridos;
  }

  /** Tiempo dentro formateado como HH:MM:SS, recalculado cada segundo. */
  tiempoVivo(v: VehiculoDentro): string {
    const totalSeg = Math.max(0, Math.floor(this.minutosVivos(v) * 60));
    const h = Math.floor(totalSeg / 3600);
    const m = Math.floor((totalSeg % 3600) / 60);
    const s = totalSeg % 60;
    const dos = (n: number) => n.toString().padStart(2, '0');
    return `${dos(h)}:${dos(m)}:${dos(s)}`;
  }

  /**
   * Costo proyectado si el vehículo saliera ahora mismo.
   * Replica la fórmula del backend: CEIL(minutos / 60) × valor_hora (solo OCASIONAL).
   * Los mensuales no pagan por hora → devuelve null ("incluido").
   */
  costoProyectado(v: VehiculoDentro): number | null {
    if (v.modalidad !== 'OCASIONAL') return null;
    const valorHora = this.tarifaPorTipo()[v.tipo_vehiculo] ?? 0;
    return Math.ceil(this.minutosVivos(v) / 60) * valorHora;
  }

  /** Abre el modal de confirmación para el vehículo de la fila. */
  pedirSalida(v: VehiculoDentro): void {
    this.confirmando.set(v);
  }

  /** Cierra el modal sin hacer nada. */
  cancelarSalida(): void {
    this.confirmando.set(null);
  }

  /** RF2 — Confirma: cierra el ingreso del vehículo y muestra el cobro. */
  confirmarSalida(): void {
    const v = this.confirmando();
    if (!v) return;

    this.error.set(null);
    this.ultimaSalida.set(null);
    this.saliendoId.set(v.id_ingreso);

    this.api.postSalida(v.id_ingreso).subscribe({
      next: (resp) => {
        this.ultimaSalida.set(resp);
        this.saliendoId.set(null);
        this.confirmando.set(null);   // cierra el modal
        this.cargar();                // refrescamos: el vehículo ya no debe aparecer
      },
      error: (err) => {
        console.error(err);
        const detail = err?.error?.detail;
        this.error.set(typeof detail === 'string' ? detail : 'No se pudo registrar la salida.');
        this.saliendoId.set(null);
        this.confirmando.set(null);
      }
    });
  }
}
