import { Component, signal, computed, inject } from '@angular/core';
import { DecimalPipe } from '@angular/common';   // habilita el pipe | number
import { Api, ReporteDia, ReporteMes } from '../../services/api';

@Component({
  selector: 'app-reportes',
  imports: [DecimalPipe],
  templateUrl: './reportes.html',
  styleUrl: './reportes.css'
})
export class ReportesComponent {
  private api = inject(Api);

  reporteDia = signal<ReporteDia[]>([]);
  reporteMes = signal<ReporteMes[]>([]);
  cargando = signal(true);
  error = signal<string | null>(null);

  // ===== Totales (señales derivadas: se recalculan solas al cambiar los datos) =====
  totalesDia = computed(() => {
    const filas = this.reporteDia();
    return {
      total_ingresos:        filas.reduce((s, f) => s + f.total_ingresos, 0),
      ocasionales:           filas.reduce((s, f) => s + f.ocasionales, 0),
      mensuales:             filas.reduce((s, f) => s + f.mensuales, 0),
      recaudado_ocasionales: filas.reduce((s, f) => s + f.recaudado_ocasionales, 0),
    };
  });

  totalesMes = computed(() => {
    const filas = this.reporteMes();
    return {
      ingresos_ocasionales:    filas.reduce((s, f) => s + f.ingresos_ocasionales, 0),
      ingresos_mensuales:      filas.reduce((s, f) => s + f.ingresos_mensuales, 0),
      recaudado_ocasionales:   filas.reduce((s, f) => s + f.recaudado_ocasionales, 0),
      recaudado_mensualidades: filas.reduce((s, f) => s + f.recaudado_mensualidades, 0),
      total:                   filas.reduce((s, f) => s + f.recaudado_ocasionales + f.recaudado_mensualidades, 0),
    };
  });

  constructor() {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.api.getReporteDia().subscribe({
      next: (resp) => { this.reporteDia.set(resp.datos); this.cargando.set(false); },
      error: (err) => { console.error(err); this.error.set('No se pudo cargar el reporte por día.'); this.cargando.set(false); }
    });

    this.api.getReporteMes().subscribe({
      next: (resp) => this.reporteMes.set(resp.datos),
      error: (err) => { console.error(err); this.error.set('No se pudo cargar el reporte por mes.'); }
    });
  }

  /** Recaudo total de una fila mensual (ocasionales + mensualidades). */
  totalMes(f: ReporteMes): number {
    return f.recaudado_ocasionales + f.recaudado_mensualidades;
  }
}
