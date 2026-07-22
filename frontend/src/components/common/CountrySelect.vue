<template>
  <div class="field-group">
    <label v-if="label" class="field-label">
      {{ label }}<span v-if="required" class="field-required"> *</span>
    </label>
    <select
      class="field-input"
      :class="{ 'field-input--error': error }"
      :value="modelValue ?? ''"
      @change="onSelect"
    >
      <option value="">— Sélectionner un pays —</option>
      <option v-for="p in PAYS" :key="p" :value="p">{{ p }}</option>
    </select>
    <p v-if="error" class="field-error">{{ error }}</p>
    <div v-if="statutGafi === 'liste_noire'" class="gafi-badge gafi-badge--noire">
      🔴 Liste noire GAFI — Contre-mesures requises (FATF Rec. 19)
    </div>
    <div v-else-if="statutGafi === 'liste_grise'" class="gafi-badge gafi-badge--grise">
      🟠 Liste grise GAFI — Vigilance renforcée requise
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getStatutGafi } from '@/data/gafi'

const props = defineProps<{
  modelValue: string | null | undefined
  label?: string
  required?: boolean
  error?: string
}>()

const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

function onSelect(e: Event) {
  emit('update:modelValue', (e.target as HTMLSelectElement).value)
}

const statutGafi = computed(() => getStatutGafi(props.modelValue ?? ''))

// Liste ISO 3166-1 complète — noms officiels français
const PAYS: string[] = [
  'Afghanistan', 'Afrique du Sud', 'Albanie', 'Algérie', 'Allemagne',
  'Andorre', 'Angola', 'Antigua-et-Barbuda', 'Arabie saoudite', 'Argentine',
  'Arménie', 'Australie', 'Autriche', 'Azerbaïdjan',
  'Bahamas', 'Bahreïn', 'Bangladesh', 'Barbade', 'Bélarus', 'Belgique',
  'Belize', 'Bénin', 'Bhoutan', 'Birmanie', 'Bolivie',
  'Bosnie-Herzégovine', 'Botswana', 'Brésil', 'Brunéi', 'Bulgarie',
  'Burkina Faso', 'Burundi',
  'Cabo Verde', 'Cambodge', 'Cameroun', 'Canada', 'Chili', 'Chine',
  'Chypre', 'Colombie', 'Comores', 'Congo', 'Corée du Nord', 'Corée du Sud',
  'Costa Rica', "Côte d'Ivoire", 'Croatie', 'Cuba',
  'Danemark', 'Djibouti', 'Dominique',
  'Égypte', 'Émirats arabes unis', 'Équateur', 'Érythrée', 'Espagne',
  'Estonie', 'Eswatini', 'États-Unis', 'Éthiopie',
  'Fidji', 'Finlande', 'France',
  'Gabon', 'Gambie', 'Géorgie', 'Ghana', 'Grèce', 'Grenade',
  'Guatemala', 'Guinée', 'Guinée équatoriale', 'Guinée-Bissau', 'Guyana',
  'Haïti', 'Honduras', 'Hongrie',
  'Îles Cook', 'Îles Marshall', 'Îles Salomon', 'Îles Vierges britanniques',
  'Inde', 'Indonésie', 'Iran', 'Iraq', 'Irlande', 'Islande', 'Israël', 'Italie',
  'Jamaïque', 'Japon', 'Jordanie',
  'Kazakhstan', 'Kenya', 'Kirghizistan', 'Kiribati', 'Koweït',
  'Laos', 'Lesotho', 'Lettonie', 'Liban', 'Libéria', 'Libye',
  'Liechtenstein', 'Lituanie', 'Luxembourg',
  'Macédoine du Nord', 'Madagascar', 'Malaisie', 'Malawi', 'Maldives',
  'Mali', 'Malte', 'Maroc', 'Maurice', 'Mauritanie', 'Mexique',
  'Micronésie', 'Moldova', 'Monaco', 'Mongolie', 'Monténégro', 'Mozambique',
  'Myanmar',
  'Namibie', 'Nauru', 'Népal', 'Nicaragua', 'Niger', 'Nigéria', 'Niue',
  'Norvège', 'Nouvelle-Zélande',
  'Oman', 'Ouganda',
  'Pakistan', 'Palaos', 'Palestine', 'Panama', 'Papouasie-Nouvelle-Guinée',
  'Paraguay', 'Pays-Bas', 'Pérou', 'Philippines', 'Pologne', 'Portugal',
  'Qatar',
  'République centrafricaine', 'République démocratique du Congo',
  'République dominicaine', 'République tchèque', 'Roumanie',
  'Royaume-Uni', 'Russie', 'Rwanda',
  'Saint-Christophe-et-Niévès', 'Saint-Marin', 'Saint-Vincent-et-les-Grenadines',
  'Sainte-Lucie', 'Samoa', 'São Tomé-et-Príncipe', 'Sénégal', 'Serbie',
  'Seychelles', 'Sierra Leone', 'Singapour', 'Slovaquie', 'Slovénie',
  'Somalie', 'Soudan', 'Soudan du Sud', 'Sri Lanka', 'Suède', 'Suisse',
  'Suriname', 'Syrie',
  'Tadjikistan', 'Tanzanie', 'Tchad', 'Thaïlande', 'Timor oriental',
  'Togo', 'Tonga', 'Trinité-et-Tobago', 'Tunisie', 'Turkménistan', 'Turquie',
  'Tuvalu',
  'Ukraine', 'Uruguay', 'Uzbekistan',
  'Vanuatu', 'Vatican', 'Venezuela', 'Vietnam',
  'Yémen',
  'Zambie', 'Zimbabwe',
]
</script>

<style scoped>
.gafi-badge {
  margin-top: 0.375rem;
  padding: 0.25rem 0.625rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}
.gafi-badge--noire {
  background: var(--color-risk-high-bg);
  color: var(--color-risk-high);
  border: 1px solid var(--color-risk-high);
}
.gafi-badge--grise {
  background: var(--color-risk-medium-bg);
  color: var(--color-risk-medium);
  border: 1px solid var(--color-risk-medium);
}
</style>
