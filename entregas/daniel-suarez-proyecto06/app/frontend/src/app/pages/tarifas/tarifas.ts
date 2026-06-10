import { Component, signal, inject, OnDestroy } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  Api, TipoVehiculoItem, Tarifa, TarifaHistorico, TarifaIn, TarifaMensual
} from '../../services/api';
import { Toast } from '../../services/toast';
import { FormState } from '../../services/form-state';

/** Lo que se conserva de los formularios de tarifas al cambiar de módulo. */
interface EstadoTarifas {
  idTipo: number | null;
  valorHora: number | null;
  vigenteDesde: string;
  idTipoMes: number | null;
  valorMes: number | null;
}

@Component({
  selector: 'app-tarifas',
  imports: [DecimalPipe, FormsModule],
  templateUrl: './tarifas.html',
  styleUrl: './tarifas.css'
})
export class TarifasComponent implements OnDestroy {
  private api = inject(Api);
  private toast = inject(Toast);
  private formState = inject(FormState);
  private readonly formKey = 'tarifas';

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

  // --- Histórico de un tipo ---
  idTipoHistorico: number | null = null;
  historico = signal<TarifaHistorico[]>([]);
  historicoBuscado = signal(false);

  // --- Tarifas mensuales (catálogo simple, sin histórico) ---
  tarifasMensuales = signal<TarifaMensual[]>([]);
  idTipoMes: number | null = null;
  valorMes: number | null = null;
  enviandoMes = signal(false);

  constructor() {
    this.cargarTarifas();
    this.cargarTarifasMensuales();
    this.api.getTipos().subscribe({
      next: (resp) => this.tipos.set(resp.datos),
      error: (err) => { console.error(err); this.toast.error('No se pudieron cargar los tipos.'); }
    });
    this.restaurar();   // recupera lo escrito si se cambió de módulo sin enviar
  }

  /** Restaura los formularios de tarifas con lo guardado al salir del módulo (si hay). */
  private restaurar(): void {
    const s = this.formState.load<EstadoTarifas>(this.formKey);
    if (!s) return;
    this.idTipo = s.idTipo;
    this.valorHora = s.valorHora;
    this.vigenteDesde = s.vigenteDesde;
    this.idTipoMes = s.idTipoMes;
    this.valorMes = s.valorMes;
  }

  /** Al cambiar de módulo: guarda lo escrito para no perderlo al volver. */
  ngOnDestroy(): void {
    this.formState.save(this.formKey, {
      idTipo: this.idTipo,
      valorHora: this.valorHora,
      vigenteDesde: this.vigenteDesde,
      idTipoMes: this.idTipoMes,
      valorMes: this.valorMes,
    } satisfies EstadoTarifas);
  }

  cargarTarifas(): void {
    this.cargando.set(true);
    this.api.getTarifas().subscribe({
      next: (resp) => { this.tarifas.set(resp.datos); this.cargando.set(false); },
      error: (err) => { console.error(err); this.toast.error('No se pudieron cargar las tarifas.'); this.cargando.set(false); }
    });
  }

  cargarTarifasMensuales(): void {
    this.api.getTarifasMensuales().subscribe({
      next: (resp) => this.tarifasMensuales.set(resp.datos),
      error: (err) => { console.error(err); this.toast.error('No se pudieron cargar las tarifas mensuales.'); }
    });
  }

  /** Al elegir un tipo, precarga su valor mensual actual para editarlo. */
  onTipoMesChange(): void {
    const actual = this.tarifasMensuales().find((t) => t.id_tipo === this.idTipoMes);
    this.valorMes = actual ? actual.valor_mes : null;
  }

  guardarTarifaMensual(): void {
    if (this.idTipoMes === null)  { this.toast.error('Elige el tipo de vehículo.'); return; }
    if (this.valorMes === null || this.valorMes < 0) {
      this.toast.error('Escribe un valor mensual válido (≥ 0).'); return;
    }

    this.enviandoMes.set(true);
    this.api.putTarifaMensual(this.idTipoMes, this.valorMes).subscribe({
      next: (resp) => {
        this.toast.exito(`Tarifa mensual de ${resp.tipo}: $${resp.valor_mes}/mes.`);
        this.enviandoMes.set(false);
        this.idTipoMes = null;
        this.valorMes = null;
        this.cargarTarifasMensuales();
      },
      error: (err) => {
        console.error(err);
        const detail = err?.error?.detail;
        this.toast.error(typeof detail === 'string' ? detail : 'No se pudo guardar la tarifa mensual.');
        this.enviandoMes.set(false);
      }
    });
  }

  crearTarifa(): void {
    if (this.idTipo === null)   { this.toast.error('Elige el tipo de vehículo.'); return; }
    if (this.valorHora === null || this.valorHora < 0) {
      this.toast.error('Escribe un valor por hora válido (≥ 0).'); return;
    }

    const tarifa: TarifaIn = {
      id_tipo: this.idTipo,
      valor_hora: this.valorHora,
      vigente_desde: this.vigenteDesde || null,
    };

    this.enviando.set(true);
    this.api.postTarifa(tarifa).subscribe({
      next: (resp) => {
        this.toast.exito(`Tarifa configurada para ${resp.tipo}: $${resp.valor_hora}/hora (desde ${resp.vigente_desde}).`);
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
        this.toast.error(typeof detail === 'string' ? detail : 'No se pudo crear la tarifa.');
        this.enviando.set(false);
      }
    });
  }

  verHistorico(): void {
    if (this.idTipoHistorico === null) return;
    this.api.getTarifaHistorico(this.idTipoHistorico).subscribe({
      next: (resp) => { this.historico.set(resp.datos); this.historicoBuscado.set(true); },
      error: (err) => { console.error(err); this.toast.error('No se pudo cargar el histórico.'); }
    });
  }
}
