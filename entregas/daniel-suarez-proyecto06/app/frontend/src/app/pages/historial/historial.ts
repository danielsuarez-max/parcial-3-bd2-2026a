import { Component, signal, inject } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Api, IngresoHistorial } from '../../services/api';

@Component({
  selector: 'app-historial',
  imports: [DatePipe, DecimalPipe, FormsModule],
  templateUrl: './historial.html',
  styleUrl: './historial.css'
})
export class HistorialComponent {
  private api = inject(Api);

  filtroPlaca = '';                 // texto del buscador (enlazado con ngModel)
  filtroModalidad = '';             // '' = todas | 'OCASIONAL' | 'MENSUAL'
  ingresos = signal<IngresoHistorial[]>([]);
  cargando = signal(true);
  error = signal<string | null>(null);

  constructor() {
    this.cargar();   // al abrir, mostramos todo el historial
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    const placa = this.filtroPlaca.trim().toUpperCase();
    this.api.getHistorial(placa || undefined, this.filtroModalidad || undefined).subscribe({
      next: (resp) => {
        this.ingresos.set(resp.datos);
        this.cargando.set(false);
      },
      error: (err) => {
        console.error(err);
        this.error.set('No se pudo cargar el historial.');
        this.cargando.set(false);
      }
    });
  }

  limpiarFiltro(): void {
    this.filtroPlaca = '';
    this.filtroModalidad = '';
    this.cargar();
  }
}
