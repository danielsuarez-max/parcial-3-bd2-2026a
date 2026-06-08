import { Component, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  Api, TipoVehiculoItem, Tarifa, TarifaHistorico, TarifaIn, TarifaMensual
} from '../../services/api';

@Component({
  selector: 'app-tarifas',
  imports: [FormsModule],
  templateUrl: './tarifas.html',
  styleUrl: './tarifas.css'
})
export class TarifasComponent {
  private api = inject(Api);

  // --- Tarifas vigentes ---
  tarifas = signal<Tarifa[]>([]);
  cargando = signal(true);

  // --- Catálogo de tipos (para los dropdowns) ---
  tipos = signal<TipoVehiculoItem[]>([]);

  // --- Formulario de nueva tarifa ---
  idTipo: number | null = null;
  valorHora: number | null = null;
  vigenteDesde = '';            // opcional (yyyy-mm-dd); vacío = hoy en el backend
  enviando = signal(false);
  exito = signal<string | null>(null);
  error = signal<string | null>(null);

  // --- Histórico de un tipo ---
  idTipoHistorico: number | null = null;
  historico = signal<TarifaHistorico[]>([]);
  historicoBuscado = signal(false);

  // --- Tarifas mensuales (catálogo simple, sin histórico) ---
  tarifasMensuales = signal<TarifaMensual[]>([]);
  idTipoMes: number | null = null;
  valorMes: number | null = null;
  enviandoMes = signal(false);
  exitoMes = signal<string | null>(null);
  errorMes = signal<string | null>(null);

  constructor() {
    this.cargarTarifas();
    this.cargarTarifasMensuales();
    this.api.getTipos().subscribe({
      next: (resp) => this.tipos.set(resp.datos),
      error: (err) => { console.error(err); this.error.set('No se pudieron cargar los tipos.'); }
    });
  }

  cargarTarifas(): void {
    this.cargando.set(true);
    this.api.getTarifas().subscribe({
      next: (resp) => { this.tarifas.set(resp.datos); this.cargando.set(false); },
      error: (err) => { console.error(err); this.error.set('No se pudieron cargar las tarifas.'); this.cargando.set(false); }
    });
  }

  cargarTarifasMensuales(): void {
    this.api.getTarifasMensuales().subscribe({
      next: (resp) => this.tarifasMensuales.set(resp.datos),
      error: (err) => { console.error(err); this.errorMes.set('No se pudieron cargar las tarifas mensuales.'); }
    });
  }

  /** Al elegir un tipo, precarga su valor mensual actual para editarlo. */
  onTipoMesChange(): void {
    const actual = this.tarifasMensuales().find((t) => t.id_tipo === this.idTipoMes);
    this.valorMes = actual ? actual.valor_mes : null;
    this.exitoMes.set(null);
    this.errorMes.set(null);
  }

  guardarTarifaMensual(): void {
    this.exitoMes.set(null);
    this.errorMes.set(null);

    if (this.idTipoMes === null)  { this.errorMes.set('Elige el tipo de vehículo.'); return; }
    if (this.valorMes === null || this.valorMes < 0) {
      this.errorMes.set('Escribe un valor mensual válido (≥ 0).'); return;
    }

    this.enviandoMes.set(true);
    this.api.putTarifaMensual(this.idTipoMes, this.valorMes).subscribe({
      next: (resp) => {
        this.exitoMes.set(`Tarifa mensual de ${resp.tipo}: $${resp.valor_mes}/mes.`);
        this.enviandoMes.set(false);
        this.idTipoMes = null;
        this.valorMes = null;
        this.cargarTarifasMensuales();
      },
      error: (err) => {
        console.error(err);
        const detail = err?.error?.detail;
        this.errorMes.set(typeof detail === 'string' ? detail : 'No se pudo guardar la tarifa mensual.');
        this.enviandoMes.set(false);
      }
    });
  }

  crearTarifa(): void {
    this.exito.set(null);
    this.error.set(null);

    if (this.idTipo === null)   { this.error.set('Elige el tipo de vehículo.'); return; }
    if (this.valorHora === null || this.valorHora < 0) {
      this.error.set('Escribe un valor por hora válido (≥ 0).'); return;
    }

    const tarifa: TarifaIn = {
      id_tipo: this.idTipo,
      valor_hora: this.valorHora,
      vigente_desde: this.vigenteDesde || null,
    };

    this.enviando.set(true);
    this.api.postTarifa(tarifa).subscribe({
      next: (resp) => {
        this.exito.set(`Tarifa configurada para ${resp.tipo}: $${resp.valor_hora}/hora (desde ${resp.vigente_desde}).`);
        this.enviando.set(false);
        this.idTipo = null;
        this.valorHora = null;
        this.vigenteDesde = '';
        this.cargarTarifas();                 // refresca la tabla de vigentes
        if (this.idTipoHistorico !== null) {  // si había un histórico abierto, refréscalo
          this.verHistorico();
        }
      },
      error: (err) => {
        console.error(err);
        const detail = err?.error?.detail;
        this.error.set(typeof detail === 'string' ? detail : 'No se pudo crear la tarifa.');
        this.enviando.set(false);
      }
    });
  }

  verHistorico(): void {
    if (this.idTipoHistorico === null) return;
    this.api.getTarifaHistorico(this.idTipoHistorico).subscribe({
      next: (resp) => { this.historico.set(resp.datos); this.historicoBuscado.set(true); },
      error: (err) => { console.error(err); this.error.set('No se pudo cargar el histórico.'); }
    });
  }
}
