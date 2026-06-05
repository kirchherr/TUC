// TUC HAC-IR native MLIR design spike.
//
// This file is intentionally parseable with an unregistered dialect:
//
//   mlir-opt --allow-unregistered-dialect examples/mlir/tuc_hac_ir_spike.mlir
//
// It is a design artifact, not a compiled backend program.

module attributes {
  tuc.dialect = "tuc_hac.v0",
  tuc.graph_name = "mlir_design_spike",
  tuc.security_model = "declarative_data_only",
  tuc.stage = "hac-ir"
} {
  func.func @mlp_block(%a: tensor<16x32xf32>, %b: tensor<32x8xf32>) -> tensor<16x8xf32> {
    %c = "tuc_hac.matmul"(%a, %b) {
      tuc.arithmetic_ops = 8192 : i64,
      tuc.bytes_read = 3072 : i64,
      tuc.bytes_written = 512 : i64,
      tuc.layout = "row_major",
      tuc.linearity = "linear",
      tuc.max_error_budget = 2.000000e-02 : f64,
      tuc.operation_name = "projection",
      tuc.preferred_memory_domain = "analog_weight_bank"
    } : (tensor<16x32xf32>, tensor<32x8xf32>) -> tensor<16x8xf32>

    %y = "tuc_hac.elementwise"(%c) {
      tuc.arithmetic_ops = 128 : i64,
      tuc.bytes_read = 512 : i64,
      tuc.bytes_written = 512 : i64,
      tuc.layout = "row_major",
      tuc.linearity = "nonlinear",
      tuc.operation_name = "activation",
      tuc.preferred_memory_domain = "gpu_hbm",
      tuc.semantic_op = "elementwise"
    } : (tensor<16x8xf32>) -> tensor<16x8xf32>

    return %y : tensor<16x8xf32>
  }
}
