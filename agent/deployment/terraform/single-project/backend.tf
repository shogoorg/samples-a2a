terraform {
  backend "gcs" {
    bucket = "shogoorg-samples-a2a-terraform-state"
    prefix = "samples-a2a/dev"
  }
}
