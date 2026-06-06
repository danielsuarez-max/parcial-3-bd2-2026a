import { Component, signal, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Api, VehiculoDentro, SalidaOut } from '../../services/api';

@Component({
  selector: 'app-vehiculos-dentro',
  imports: [DatePipe],
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

  constructor() {
    this.cargar();
  }

  /** Pide al backend la lista de vehículos dentro. Reutilizable por el botón "Actualizar". */
  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.api.getVehiculosDentro().subscribe({
      next: (resp) => {
        this.vehiculos.set(resp.datos);
        this.cargando.set(false);
      },
      error: (err) => {
        console.error(err);
        this.error.set('No se pudo conectar con el backend. ¿Está corriendo en el puerto 8001?');
        this.cargando.set(false);
      }
    });
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
