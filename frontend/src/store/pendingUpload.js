/**
 * Temporarily store files and requirements to be uploaded
 * Used to immediately navigate after clicking Start Engine on home page, API call is made on Process page
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  numAgents: 28,
  isPending: false
})

export function setPendingUpload(files, requirement, numAgents = 28) {
  state.files = files
  state.simulationRequirement = requirement
  state.numAgents = numAgents
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    numAgents: state.numAgents,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.numAgents = 28
  state.isPending = false
}

export default state
