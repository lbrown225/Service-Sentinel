variable "candidate_image_tag" {
  description = "Immutable Git SHA tag for the candidate Lambda image"
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{12,40}$", var.candidate_image_tag))
    error_message = "candidate_image_tag must be a 12- to 40-character lowercase hexadecimal Git SHA."
  }
}

variable "monitor_schedule_enabled" {
  description = "Whether the recurring monitor schedule is active"
  type        = bool
  default     = false
}
